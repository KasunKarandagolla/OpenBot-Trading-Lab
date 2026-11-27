"""Read-only structurally verified OpenCode normalized session/part adapter.

Only the retained provider tables needed for one exact parent or child turn are
read. Assistant ``session_message.content`` is not a content source: the
observed runtime leaves it empty and stores text and tool parts in
``session_part``. Reasoning parts are structurally validated but their text is
never returned or published. Unknown schemas, ambiguous ordering, duplicate
native calls and modified evidence pages fail closed.

This module never executes recorded JavaScript. The narrow parser accepts only
the exact Code Mode wrapper used for ``tools.openbot.tool_describe`` and
``tools.openbot.tool_call`` and decodes their literal argument object.
"""
import json
import re
from datetime import datetime, timedelta, timezone

from .contracts import ContractError, digest, encode, utc
from .native_identity import NativeEvidenceError, checked_path, read_db, ref

SCHEMA = 'OPENCODE_V2_SESSION_PART'
# The first qualified session-part records observed on this host used 2.4.1.
# This is diagnostic provenance only: compatibility is determined from the
# required records and semantics below, never from a version allowlist.
SESSION_VERSION = '2.4.1'
# The session_message adapter predates normalized session_part records. These
# exact versions were observed for retained historical OpenCode replay.
LEGACY_SESSION_VERSIONS = frozenset({'2.2.5', '2.2.6', '2.3.0'})
# Diagnostic labels are fixed; they never contain provider values or text.
_VARIANT = 'OPENCODE_SESSION_PART'
_MESSAGE_TYPES = frozenset({'user', 'assistant', 'idle', 'model-switched'})
_PART_TYPES = frozenset({'reasoning', 'text', 'tool'})
_STRICT_TOOLS = frozenset({'shell', 'execute'})
_REQUIRED_TOOLS = {'openbot.start_task': {'title', 'brief'},
    'openbot.attach_files_to_response': {'paths'}}
_EXECUTE = re.compile(r'const[ \t\r\n]+r[ \t\r\n]*=[ \t\r\n]*await[ \t\r\n]+'
    r'tools\.openbot\.(tool_describe|tool_call)[ \t\r\n]*\(')
_TAIL = re.compile(r'\)[ \t\r\n]*;[ \t\r\n]*(?:return[ \t\r\n]+r|text[ \t\r\n]*\([ \t\r\n]*r[ \t\r\n]*\))'
    r'[ \t\r\n]*;?[ \t\r\n]*')
_MAX_TOOL_TEXT = 256 * 1024


def _fail(code, stage, check, variant=_VARIANT):
    raise NativeEvidenceError(code, stage, check, variant)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def _obj(raw, *, stage='EVIDENCE', check='JSON'):
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
    except (ValueError, TypeError, RecursionError):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', stage, check)
    if not isinstance(value, dict):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', stage, check)
    return value


def _text_content(value):
    if (not isinstance(value, list) or len(value) != 1
            or not isinstance(value[0], dict) or set(value[0]) != {'type', 'text'}
            or value[0]['type'] != 'text' or not isinstance(value[0]['text'], str)
            or len(value[0]['text'].encode()) > _MAX_TOOL_TEXT):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'CONTENT_MISMATCH')
    return value[0]['text']


def _millis(value, *, stage='ENVELOPE'):
    if type(value) is not int or value < 0:
        _fail('NATIVE_REVIEW_INCOMPLETE', stage, 'TIMESTAMP')
    return value


def _moment(value):
    """Convert a retained provider millisecond timestamp to aware UTC."""
    try:
        return datetime.fromtimestamp(_millis(value) / 1000, timezone.utc)
    except (OverflowError, OSError, ValueError):
        _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'TIMESTAMP')


def _at(value):
    """Accept an existing ISO timestamp or an aware datetime; never local time."""
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'TIMESTAMP')
        return value.astimezone(timezone.utc)
    try:
        return utc(value)
    except ContractError:
        _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'TIMESTAMP')


def _model_parts(model):
    if not isinstance(model, str) or model.count('/') != 1:
        raise ContractError('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
    provider, name = model.split('/', 1)
    if not provider or not name:
        raise ContractError('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED')
    return provider, name


def _model_matches(record, name, provider, effort):
    if not isinstance(record, dict) or set(record) - {'id', 'providerID', 'variant'}:
        return False
    if record.get('id') != name or record.get('providerID') != provider:
        return False
    if 'variant' in record and not isinstance(record['variant'], str):
        return False
    return effort is None or record.get('variant') == effort


def session_record(config, session, *, allowed_versions=None):
    """Validate the normalized session identity and retain its version.

    The compact session-part adapter accepts a new version only when the
    required table/field shape and turn evidence still pass the structural
    readers. ``allowed_versions`` remains available for historical callers
    whose message-level semantics were qualified only for specific versions.
    """
    with read_db(config['provider_db']) as db:
        row = db.execute('SELECT id,parent_id,version,model FROM session_v2 WHERE id=?',
                         (session,)).fetchone()
    if not row or row[0] != session:
        raise ContractError('NATIVE_SESSION_MISMATCH')
    _, parent, version, raw_model = row
    if (not isinstance(version, str) or not version.strip() or len(version) > 64
            or re.fullmatch(r'[0-9A-Za-z][0-9A-Za-z.+_-]*', version) is None
            or allowed_versions is not None and version not in allowed_versions):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'SESSION', 'VERSION')
    model = _obj(raw_model, stage='SESSION', check='IDENTITY')
    provider = model.get('providerID')
    name = model.get('id')
    variant = model.get('variant')
    if (not isinstance(provider, str) or not provider or not isinstance(name, str) or not name
            or set(model) - {'id', 'providerID', 'variant'}
            or variant is not None and (not isinstance(variant, str) or not variant)):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'SESSION', 'IDENTITY')
    return {'id': session, 'parent_id': parent, 'version': version,
        'model': f'{provider}/{name}',
        'provider': provider, 'name': name, 'effort': variant}


def assert_session_identity(config, session, *, model, provider, effort=None):
    info = session_record(config, session)
    if info['model'] != model or info['provider'] != provider:
        _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'APP_CHILD_MODEL')
    if effort is not None and info['effort'] != effort:
        _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'ROLLOUT_SETTINGS_MODEL')
    return info


_ASSISTANT_FIELDS = frozenset({'agent', 'model', 'content', 'finish', 'rawFinish',
                               'time', 'tokens', 'cost'})


def _assistant_envelope(message, created, *, allow_incomplete):
    """Validate a completed envelope strictly or recognize a bounded live prefix.

    OpenCode 2.4.2's exact transient envelope was not retained. Active reads
    therefore accept only subsets of the already observed completed field set,
    with the provider row's creation timestamp still bound inside ``time``.
    This recognizes an in-flight record; it does not make its parts evidence.
    """
    if set(message) - _ASSISTANT_FIELDS:
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_KEYS')
    stamp = message.get('time')
    if not isinstance(stamp, dict) or stamp.get('created') != created:
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'TIMESTAMP')
    completed = stamp.get('completed')
    incomplete = completed is None
    if incomplete:
        if not allow_incomplete:
            _fail('NATIVE_REVIEW_INCOMPLETE', 'EVIDENCE', 'INCOMPLETE_NOT_ALLOWED')
        checks = (
            ('agent', lambda value: isinstance(value, str), 'ASSISTANT_AGENT'),
            ('model', lambda value: isinstance(value, dict), 'ASSISTANT_MODEL'),
            ('content', lambda value: value == [], 'ASSISTANT_CONTENT'),
            # A terminal stop is completion evidence; without its completion
            # timestamp it is malformed, not an active prefix.
            ('finish', lambda value: value in ('tool-calls', None), 'ASSISTANT_FINISH'),
            ('rawFinish', lambda value: isinstance(value, (str, type(None))),
             'ASSISTANT_RAW_FINISH'),
            ('tokens', lambda value: isinstance(value, dict), 'ASSISTANT_TOKENS'),
            ('cost', lambda value: value is None or type(value) in {int, float},
             'ASSISTANT_COST'),
        )
        for field, valid, check in checks:
            if field in message and not valid(message[field]):
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', check)
        return True

    if type(completed) is not int or completed < created:
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_COMPLETION')
    if set(message) != _ASSISTANT_FIELDS:
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_KEYS')
    if not isinstance(message['agent'], str):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_AGENT')
    if not isinstance(message['model'], dict):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_MODEL')
    if message['content'] != []:
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_CONTENT')
    if message['finish'] not in ('tool-calls', 'stop', None):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_FINISH')
    if not isinstance(message['rawFinish'], (str, type(None))):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_RAW_FINISH')
    if not isinstance(message['tokens'], dict):
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_TOKENS')
    if type(message['cost']) not in {int, float}:
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'ASSISTANT_COST')
    return False


def _message_rows(db, session, start, end, *, allow_incomplete=False):
    rows = db.execute('''SELECT id,type,seq,time_created,time_updated,data
        FROM session_message WHERE session_id=? ORDER BY time_created,seq''',
        (session,)).fetchall()
    selected = []
    previous = None
    for mid, kind, seq, created, updated, data in rows:
        _millis(created); _millis(updated)
        if type(seq) is not int or seq < 0 or not isinstance(mid, str) or not mid:
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'ORDER')
        if updated < created:
            _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'TIMESTAMP')
        key = (created, seq)
        if previous is not None and key <= previous:
            _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'ORDER')
        previous = key
        moment = _moment(created)
        if moment < start - timedelta(seconds=1) or moment > end + timedelta(seconds=1):
            continue
        if kind not in _MESSAGE_TYPES:
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'JSON')
        message = _obj(data, stage='ENVELOPE', check='JSON')
        if (not isinstance(message.get('time'), dict)
                or message['time'].get('created') != created):
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'TIMESTAMP')
        if kind == 'user':
            # The retained runtime records the user's file list on every turn.
            # Attachments are not part of the review transport, so only an
            # explicitly empty list is accepted.
            if (set(message) not in ({'time', 'text'}, {'time', 'text', 'files'})
                    or not isinstance(message['text'], str)
                    or len(message['text'].encode()) > 2 * 1024 * 1024
                    or 'files' in message and message['files'] != []):
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'CONTENT_MISMATCH')
        elif kind == 'assistant':
            message['_incomplete'] = _assistant_envelope(
                message, created, allow_incomplete=allow_incomplete)
        elif kind == 'model-switched':
            if (set(message) - {'time', 'model', 'previous'} or not isinstance(message['model'], dict)
                    or 'previous' in message and not isinstance(message['previous'], dict)):
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'IDENTITY', 'SCHEMA_MISMATCH')
        elif (set(message) - {'time', 'outcome'} or not isinstance(message.get('outcome'), str)):
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'JSON')
        selected.append({'id': mid, 'type': kind, 'seq': seq, 'created': created,
            'updated': updated, 'moment': moment, 'data': message})
    incomplete = [index for index, message in enumerate(selected)
                  if message['type'] == 'assistant' and message['data'].get('_incomplete')]
    if len(incomplete) > 1:
        _fail('NATIVE_REVIEW_INCOMPLETE', 'EVIDENCE', 'INCOMPLETE_MULTIPLE')
    if incomplete and incomplete[0] != len(selected) - 1:
        _fail('NATIVE_REVIEW_INCOMPLETE', 'EVIDENCE', 'INCOMPLETE_NOT_FINAL')
    return selected


def _part_rows(db, session, messages):
    wanted = {message['id']: message for message in messages}
    rows = db.execute('''SELECT message_id,ordinal,type,call_id,time_created,time_updated,data
        FROM session_part WHERE session_id=? ORDER BY time_created,ordinal''',
        (session,)).fetchall()
    seen = set()
    by_message = {}
    ordinals_by_message = {}
    for mid, ordinal, kind, call_id, created, updated, data in rows:
        if (not isinstance(mid, str) or type(ordinal) is not int or ordinal < 0
                or (mid, ordinal) in seen):
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'ORDER')
        seen.add((mid, ordinal)); _millis(created); _millis(updated)
        if mid not in wanted:
            continue
        message = wanted[mid]
        if message['type'] == 'assistant' and message['data'].get('_incomplete'):
            # Do not let any part from an unfinished assistant envelope prove
            # discovery, submission, shell execution or a final response.
            continue
        ordinals_by_message.setdefault(mid, []).append(ordinal)
        if not message['created'] <= created <= updated <= message['updated']:
            _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'TIMESTAMP')
        raw_part = _obj(data, stage='EVIDENCE', check='JSON')
        if kind not in _PART_TYPES:
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'JSON')
        part_time = raw_part.get('time')
        raw_completed = part_time.get('completed') if isinstance(part_time, dict) else None
        if kind == 'tool':
            if raw_completed is None:
                _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'TIMESTAMP')
            if type(raw_completed) is not int or raw_completed < created:
                _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'TIMESTAMP')
        elif raw_completed is not None and (type(raw_completed) is not int or raw_completed < created):
            _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'TIMESTAMP')
        part = raw_part
        if part.get('type') != kind:
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'JSON')
        if kind == 'reasoning':
            if (not isinstance(part.get('text'), str)
                    or set(part) - {'type', 'text', 'native', 'time'}
                    or 'native' in part and not isinstance(part['native'], dict)):
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'SCHEMA_MISMATCH')
        elif kind == 'text':
            if (not isinstance(part.get('text'), str)
                    or set(part) not in ({'type', 'text'}, {'type', 'text', 'time'})):
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'FINAL')
        else:
            if set(part) != {'type', 'id', 'name', 'executed', 'state', 'time'}:
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'SCHEMA_MISMATCH')
            if (not isinstance(part.get('id'), str) or not part['id']
                    or not isinstance(part.get('name'), str) or not part['name']
                    or type(part.get('executed')) is not bool
                    or not isinstance(part.get('state'), dict)
                    or not isinstance(part.get('time'), dict)):
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'SCHEMA_MISMATCH')
            if call_id != part['id'] or part['time'].get('created') != created:
                _fail('NATIVE_SESSION_MISMATCH', 'EVIDENCE', 'IDENTITY')
            completed = part['time'].get('completed')
            if type(completed) is not int or completed < created:
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'TIMESTAMP')
            state = part['state']
            if not isinstance(state.get('status'), str) or not isinstance(state.get('input'), dict) \
                    or not isinstance(state.get('metadata'), dict) or not isinstance(state.get('content'), list):
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'SCHEMA_MISMATCH')
            if part['name'] in _STRICT_TOOLS:
                if set(state) != {'status', 'input', 'content', 'metadata'}:
                    _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'SCHEMA_MISMATCH')
                if state['status'] not in {'completed', 'error'}:
                    _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'COMPLETION_MISMATCH')
                if part['name'] == 'execute' and state['status'] == 'completed':
                    calls = state['metadata'].get('toolCalls')
                    if (state['metadata'].get('truncated') is not False
                            or not isinstance(calls, list) or not calls):
                        _fail('NATIVE_UNAUTHORIZED_TOOL', 'EVIDENCE', 'TOOLS')
        if kind != 'tool' and call_id is not None:
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'ORDER')
        if kind in {'reasoning', 'text'} and 'time' in part:
            stamp = part['time']
            if (not isinstance(stamp, dict) or stamp.get('created') != created
                    or 'completed' in stamp and (type(stamp['completed']) is not int
                        or stamp['completed'] < created)):
                _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'ENVELOPE', 'TIMESTAMP')
        by_message.setdefault(mid, []).append({'ordinal': ordinal, 'type': kind,
            'created': created, 'updated': updated, 'data': part})
    result = []
    for message in messages:
        parts = by_message.get(message['id'], [])
        ordinals = sorted(ordinals_by_message.get(message['id'], []))
        if ordinals != list(range(len(ordinals))):
            _fail('NATIVE_REVIEW_INCOMPLETE', 'ENVELOPE', 'ORDER')
        if message['type'] == 'assistant' and not parts and not message['data'].get('_incomplete'):
            _fail('NATIVE_REVIEW_INCOMPLETE', 'EVIDENCE', 'COMPLETENESS')
        if message['type'] != 'assistant' and parts:
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'COMPLETENESS')
        for part in parts:
            result.append({**part, 'message': message})
    return result


def turn_parts(config, session, start, end, *, allow_incomplete=False):
    """Read messages and parts from one provider-DB snapshot, without reasoning."""
    with read_db(config['provider_db']) as db:
        # sqlite3 does not implicitly begin a transaction for SELECTs. Start
        # one before either table read so a poll cannot combine message rows
        # from one provider write with parts from a later write.
        db.execute('BEGIN')
        messages = _message_rows(db, session, _at(start), _at(end),
                                 allow_incomplete=allow_incomplete)
        if not messages:
            raise ContractError('NATIVE_NOT_INVOKED')
        parts = _part_rows(db, session, messages)
    return messages, parts


def assert_model(messages, *, model, provider, effort=None, allow_empty=False):
    """Every assistant record in the turn must keep the frozen identity."""
    name = _model_parts(model)[1] if model.startswith(provider + '/') else None
    if name is None:
        _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'IDENTITY', 'SCHEMA_MISMATCH')
    users = [message for message in messages if message['type'] == 'user']
    if not users:
        if allow_empty:
            return 0
        raise ContractError('NATIVE_NOT_INVOKED')
    first_user = users[0]['created']
    seen = 0
    for message in messages:
        if message['type'] == 'assistant':
            seen += 1
            if (message['data'].get('_incomplete') and 'model' not in message['data']):
                # Session identity was independently checked by session_record;
                # an unfinished envelope may not have published its model yet.
                continue
            if not _model_matches(message['data'].get('model'), name, provider, effort):
                _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'APP_CHILD_MODEL')
        elif message['type'] == 'model-switched':
            # The runtime records the initial default variant immediately before
            # the first user message. Only selections made during the turn are
            # mid-run changes.
            selected = message['data']['model']
            required = effort if message['created'] >= first_user else None
            if not _model_matches(selected, name, provider, required):
                _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY',
                      'ROLLOUT_SETTINGS_MODEL' if required is not None else 'APP_CHILD_MODEL')
    if not seen and not allow_empty:
        raise ContractError('NATIVE_NOT_INVOKED')
    return seen


class _Literals:
    """Parse only JSON-like literals inside one recorded JavaScript call."""

    def __init__(self, text):
        self.text = text
        self.i = 0

    def _space(self):
        while self.i < len(self.text) and self.text[self.i] in ' \t\r\n':
            self.i += 1

    def _string(self):
        try:
            value, self.i = json.JSONDecoder().raw_decode(self.text, self.i)
        except (ValueError, RecursionError):
            raise ValueError() from None
        if not isinstance(value, str):
            raise ValueError()
        return value

    def _key(self):
        self._space()
        if self.i < len(self.text) and self.text[self.i] == '"':
            return self._string()
        match = re.match(r'[A-Za-z_$][A-Za-z0-9_$]*', self.text[self.i:])
        if match is None:
            raise ValueError()
        self.i += match.end()
        return match.group()

    def value(self):
        self._space()
        if self.i >= len(self.text):
            raise ValueError()
        char = self.text[self.i]
        if char == '{':
            self.i += 1
            result = {}
            self._space()
            if self.i < len(self.text) and self.text[self.i] == '}':
                self.i += 1
                return result
            while True:
                key = self._key()
                if key in result:
                    raise ValueError()
                self._space()
                if self.i >= len(self.text) or self.text[self.i] != ':':
                    raise ValueError()
                self.i += 1
                result[key] = self.value()
                self._space()
                if self.i < len(self.text) and self.text[self.i] == ',':
                    self.i += 1
                    continue
                if self.i < len(self.text) and self.text[self.i] == '}':
                    self.i += 1
                    return result
                raise ValueError()
        if char == '[':
            self.i += 1
            result = []
            self._space()
            if self.i < len(self.text) and self.text[self.i] == ']':
                self.i += 1
                return result
            while True:
                result.append(self.value())
                self._space()
                if self.i < len(self.text) and self.text[self.i] == ',':
                    self.i += 1
                    continue
                if self.i < len(self.text) and self.text[self.i] == ']':
                    self.i += 1
                    return result
                raise ValueError()
        if char == '"':
            return self._string()
        if char in '-0123456789':
            match = re.match(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',
                             self.text[self.i:])
            if match is None:
                raise ValueError()
            self.i += match.end()
            return json.loads(match.group())
        for literal, value in (('true', True), ('false', False), ('null', None)):
            if self.text.startswith(literal, self.i):
                self.i += len(literal)
                return value
        raise ValueError()


def parse_execute(script):
    """Decode one exact permitted Code Mode wrapper; never evaluate code."""
    if not isinstance(script, str) or not script or len(script.encode()) > 32768:
        raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
    match = _EXECUTE.match(script)
    if match is None:
        raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
    reader = _Literals(script)
    reader.i = match.end()
    try:
        argument = reader.value()
    except (ValueError, RecursionError):
        raise ContractError('NATIVE_UNAUTHORIZED_TOOL') from None
    if _TAIL.fullmatch(script, reader.i) is None:
        raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
    return {'method': match.group(1), 'argument': argument}


def _execute_parts(parts):
    for part in parts:
        if part['type'] != 'tool' or part['data']['name'] != 'execute':
            continue
        state = part['data']['state']
        metadata = state['metadata']
        if set(metadata) - {'toolCalls', 'truncated', 'error'}:
            _fail('NATIVE_PROVIDER_SCHEMA_UNSUPPORTED', 'EVIDENCE', 'SCHEMA_MISMATCH')
        if metadata.get('truncated') is not False:
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        calls = metadata.get('toolCalls')
        if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict):
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        call = calls[0]
        if (set(call) != {'tool', 'status', 'input'} or not isinstance(call.get('tool'), str)
                or call.get('status') not in {'completed', 'error'}
                or not isinstance(call.get('input'), dict)):
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        yield part, call


def _valid_schema(name, schema):
    if not isinstance(schema, dict) or schema.get('type') != 'object' \
            or schema.get('additionalProperties') is not False:
        return False
    properties = schema.get('properties')
    required = schema.get('required')
    if not isinstance(properties, dict) or not isinstance(required, list):
        return False
    if name == 'openbot.start_task':
        return (set(properties) == {'title', 'brief'} and set(required) == {'title', 'brief'}
                and all(properties[key].get('type') == 'string' for key in ('title', 'brief')))
    if name == 'openbot.attach_files_to_response':
        return (set(properties) == {'paths', 'folder'} and set(required) == {'paths'}
                and properties['paths'].get('type') == 'array'
                and properties['paths'].get('items', {}).get('type') == 'string'
                and properties['folder'].get('type') == 'string')
    return False


def _discovery_result(text):
    result = _obj(text, stage='TOOL_DISCOVERY', check='CONTENT_MISMATCH')
    if (set(result) != {'call', 'guidance', 'tools'} or not isinstance(result['call'], str)
            or not isinstance(result['guidance'], list)):
        _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'CONTENT_MISMATCH')
    discovered = set()
    for tool in result['tools']:
        if (not isinstance(tool, dict) or set(tool) - {'name', 'description', 'inputSchema'}
                or not isinstance(tool.get('name'), str)):
            _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'CONTENT_MISMATCH')
        if tool['name'] in _REQUIRED_TOOLS:
            if tool['name'] in discovered or not _valid_schema(tool['name'], tool.get('inputSchema')):
                _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'SCHEMA_MISMATCH')
            discovered.add(tool['name'])
    return discovered


def attest_smoke_discovery(identity, config, *, as_of):
    """Bind both exact schemas to a successful current-turn discovery."""
    from .native_identity import parent_binding
    binding = parent_binding(identity, config, require_configured_model=True, as_of=as_of)
    start = _at(binding['started_at'])
    end = min(_at(binding['completed_at']), _at(as_of)) if binding['completed_at'] else _at(as_of)
    messages, parts = turn_parts(config, binding['external'], start, end,
                                 allow_incomplete=binding.get('status') != 'completed')
    assert_model(messages, model=identity['model'], provider=identity['provider'],
                 effort=identity.get('effort'), allow_empty=True)
    calls = completed = 0
    found = None
    for part, call in _execute_parts(parts):
        state = part['data']['state']
        tool = call['tool']
        input_name = call['input'].get('name')
        try:
            parsed = parse_execute(state['input'].get('code'))
        except ContractError:
            if (tool == 'openbot.tool_describe'
                    or tool == 'openbot.tool_call' and input_name == 'openbot.tool_describe'):
                _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'INVALID_CALL')
            if tool == 'openbot.tool_call' and input_name == 'openbot.start_task':
                # The submission attester owns malformed start_task attempts.
                continue
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL') from None
        argument = parsed['argument']
        if parsed['method'] == 'tool_describe':
            if tool != 'openbot.tool_describe':
                if tool == 'openbot.tool_call' and input_name == 'openbot.tool_describe':
                    # The runtime can record a nested wrapper that fails. It is
                    # an attempt, never a successful discovery.
                    calls += 1
                    if state['status'] == 'completed' or call['status'] == 'completed':
                        _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY',
                              'INVALID_CALL')
                    continue
                raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
            if (not isinstance(argument, dict) or set(argument) != {'names'}
                    or not isinstance(argument['names'], list)
                    or not argument['names']
                    or not all(isinstance(name, str) for name in argument['names'])
                    or len(set(argument['names'])) != len(argument['names'])
                    or set(argument['names']) != set(_REQUIRED_TOOLS)):
                _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'INVALID_CALL')
            if call['input'] != {'names': argument['names']}:
                raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
            calls += 1
            if state['status'] != 'completed' or call['status'] != 'completed':
                continue
            completed += 1
            discovered = _discovery_result(_text_content(state['content']))
            if discovered != set(_REQUIRED_TOOLS):
                _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'SCHEMA_MISMATCH')
            if found is not None:
                _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'DUPLICATE_CALL')
            found = sorted(discovered)
            continue
        if tool != 'openbot.tool_call':
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        if input_name == 'openbot.tool_describe':
            # A nested wrapper can be recorded when the runtime rejects the
            # call. It is an attempt, never a successful discovery.
            if (not isinstance(argument, dict) or set(argument) != {'name', 'arguments'}
                    or argument.get('name') != 'openbot.tool_describe'
                    or call['input'] != argument):
                _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'INVALID_CALL')
            calls += 1
            if state['status'] == 'completed' or call['status'] == 'completed':
                _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', 'INVALID_CALL')
            continue
        if (not isinstance(argument, dict) or set(argument) != {'name', 'arguments'}
                or argument.get('name') not in _REQUIRED_TOOLS
                or not isinstance(argument.get('arguments'), dict)):
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        if call['input'] != argument or input_name != argument['name']:
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
    if found is None:
        check = ('NO_CALL' if not calls else 'NO_COMPLETION' if not completed
                 else 'COMPLETION_MISMATCH')
        _fail('NATIVE_TOOL_DISCOVERY_UNVERIFIED', 'TOOL_DISCOVERY', check)
    return {'status': 'VERIFIED_CURRENT_PARENT_TOOL_DISCOVERY', 'tools': found,
        'provider_session_version': binding.get('provider_session_version')}


def _submission_text(result):
    if (not isinstance(result, dict) or set(result) - {'taskId', 'title', 'note'}
            or not isinstance(result.get('taskId'), str) or not result['taskId']
            or not isinstance(result.get('title'), str)):
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    return result


def observe_submission(config, identity, request_at, arguments, *, as_of, reserved_at=None,
                       require_configured_model=True):
    """Observe exactly one scoped start_task call and its exact acknowledgment."""
    from .native_identity import parent_binding
    binding = parent_binding(identity, config, require_configured_model=require_configured_model,
                             as_of=as_of)
    start = _at(binding['started_at'])
    end = min(_at(binding['completed_at']), _at(as_of)) if binding['completed_at'] else _at(as_of)
    messages, parts = turn_parts(config, binding['external'], start, end,
                                 allow_incomplete=binding.get('status') != 'completed')
    if not any(message['type'] == 'assistant' for message in messages):
        return {'submission_state': 'NOT_OBSERVED', 'submission_attempts': 0}
    assert_model(messages, model=identity['model'], provider=identity['provider'],
                 effort=identity.get('effort'), allow_empty=True)
    request_moment = _at(request_at)
    reserved_moment = _at(reserved_at) if reserved_at is not None else None
    attempts = []
    for part, call in _execute_parts(parts):
        state = part['data']['state']
        input_name = call['input'].get('name')
        declared = call['tool'] == 'openbot.tool_call' and input_name == 'openbot.start_task'
        at = _moment(part['created'])
        if at < request_moment:
            # A pre-request call is outside this ticket's observation window.
            continue
        if reserved_moment is not None and at < reserved_moment:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        try:
            parsed = parse_execute(state['input'].get('code'))
        except ContractError:
            if declared:
                raise ContractError('NATIVE_HANDOFF_UNATTESTED') from None
            continue
        argument = parsed['argument']
        candidate = declared or (isinstance(argument, dict)
                                 and argument.get('name') == 'openbot.start_task')
        if not candidate:
            continue
        if (parsed['method'] != 'tool_call' or not isinstance(argument, dict)
                or set(argument) != {'name', 'arguments'}
                or argument.get('name') != 'openbot.start_task'
                or not isinstance(argument.get('arguments'), dict)):
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        if (call['tool'] != 'openbot.tool_call' or call['input'] != argument
                or input_name != 'openbot.start_task'):
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        if argument['arguments'] != arguments:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        attempts.append((part, call, at))
    if not attempts:
        return {'submission_state': 'NOT_OBSERVED', 'submission_attempts': 0}
    if len(attempts) != 1:
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    part, call, at = attempts[0]
    state = part['data']['state']
    result = {'submission_attempts': 1, 'attempted_at_utc': at.isoformat()}
    if state['status'] == 'error' or call['status'] == 'error':
        title, brief = arguments.get('title'), arguments.get('brief')
        oversize = ((isinstance(title, str) and len(title.strip()) > 120) or
                    (isinstance(brief, str) and len(brief.strip().encode(
                        'utf-16-le', errors='surrogatepass')) // 2 > 100000))
        return {**result, 'submission_state': 'REJECTED', 'submission_error':
                'NATIVE_TOOL_INPUT_SIZE_REJECTED' if oversize else 'NATIVE_TOOL_REJECTED'}
    if state['status'] != 'completed' or call['status'] != 'completed':
        return {**result, 'submission_state': 'ATTEMPTED'}
    response = _submission_text(_obj(_text_content(state['content']), stage='EVIDENCE',
                                     check='CONTENT_MISMATCH'))
    if response['title'] != arguments['title']:
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    responded = _moment(part['data']['time']['completed'])
    if responded < at:
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    return {**result, 'responded_at_utc': responded.isoformat(),
            'submission_state': 'ACKNOWLEDGED',
            'acknowledged_task_ref': ref(response['taskId'])}


def attest_handoff(config, identity, request, *, as_of, require_configured_model=True):
    from .native_codex import review_brief
    args = {'title': 'OPENBOT-RESEARCH-' + request['material_sha256'],
            'brief': review_brief(request)}
    observed = observe_submission(config, identity, request['as_of_utc'], args, as_of=as_of,
                                  require_configured_model=require_configured_model)
    if observed['submission_state'] == 'ACKNOWLEDGED':
        return True
    raise ContractError('NATIVE_HANDOFF_UNATTESTED')


def _page_command(directory, material, page):
    from .native_handoff import _page_argv, wsl_root
    root = wsl_root().replace("'", "''")
    return (f"wsl.exe --cd '{root}' -- " + ' '.join(_page_argv(directory, material, None))
            + ' ' + str(page))


def _page_output(text, page):
    # ``review-page`` writes the frame without a trailing newline. A shell
    # transport may append exactly one line terminator; nothing else is
    # normalized, so modified or truncated page bytes never match.
    return text == page or text == page + '\n' or text == page + '\r\n'


def _tool_state(part):
    state = part['data']['state']
    metadata = state['metadata']
    if (state['status'] != 'completed' or metadata.get('status') != 'completed'
            or metadata.get('truncated') is not False
            or type(metadata.get('exit')) is not int or metadata['exit'] != 0):
        raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
    if set(state['input']) != {'command'} or not isinstance(state['input']['command'], str):
        raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
    return state


def attest(config, session, turn, *, model, workspace, start, end, expected_input, expected_reply,
           backend=None, evidence=None, require_thread_model=True, effort=None):
    """Attest one child turn: exact input, ordered pages, final text and model."""
    provider = backend if isinstance(backend, str) and backend and '/' not in backend \
        else _model_parts(model)[0]
    info = assert_session_identity(config, session, model=model, provider=provider,
                                   effort=effort if require_thread_model else None)
    messages, parts = turn_parts(config, session, start, end)
    assert_model(messages, model=model, provider=provider, effort=info['effort'])
    users = [message for message in messages if message['type'] == 'user']
    assistants = [message for message in messages if message['type'] == 'assistant']
    if len(users) != 1 or not assistants:
        raise ContractError('NATIVE_READ_INCOMPLETE')
    if users[0]['data']['text'].count(expected_input) != 1:
        raise ContractError('NATIVE_READ_INCOMPLETE')
    final = assistants[-1]
    if final['data']['finish'] != 'stop' or any(message['created'] > final['created']
                                               for message in assistants):
        raise ContractError('NATIVE_REVIEW_INCOMPLETE')
    final_parts = [part for part in parts if part['message']['id'] == final['id']]
    texts = [part for part in final_parts if part['type'] == 'text']
    if len(texts) != 1 or final_parts[-1] is not texts[0]:
        raise ContractError('NATIVE_REPLY_PROVENANCE')
    if texts[0]['data']['text'] != expected_reply:
        raise ContractError('NATIVE_REPLY_PROVENANCE')
    directory, material, pages = evidence if evidence is not None else (None, None, ())
    delivered = []
    for part in parts:
        if part['type'] != 'tool':
            continue
        if part['data']['name'] != 'shell':
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        state = _tool_state(part)
        if evidence is None:
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        page = None
        for number in range(1, len(pages) + 1):
            if state['input']['command'] == _page_command(directory, material, number):
                page = number
                break
        if page is None or page in delivered or page != len(delivered) + 1:
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        if not _page_output(_text_content(state['content']), pages[page - 1]):
            raise ContractError('NATIVE_READ_INCOMPLETE')
        delivered.append(page)
    if evidence is not None and delivered != list(range(1, len(pages) + 1)):
        raise ContractError('NATIVE_READ_INCOMPLETE')
    usage = [{'finish': message['data']['finish'], 'tokens': message['data']['tokens'],
              'reported_cost_usd': message['data']['cost']} for message in assistants]
    return {'provider_schema': SCHEMA, 'schema_variant': _VARIANT,
        'provider_session_version': info['version'],
        'model_requests': len(assistants), 'provider_usage': usage,
        'tool_operations': ['READ_SKILL', 'READ_REQUEST'] if evidence is not None else [],
        'unauthorized_tool_operations': 0, 'skill_and_request_read_completely': True,
        'read_methods': ['EXACT_HASH_BOUND_PAGES_IN_PROVIDER_TOOL_OUTPUT']
            if evidence is not None else
            ['EXACT_INLINE_SKILL_AND_REQUEST_IN_PROVIDER_USER_MESSAGE'],
        'native_session_ref': ref(session), 'native_turn_ref': ref(turn),
        'input_proof': 'PROVIDER_ATTESTED_COMPLETE_INPUT_BYTES; NOT_A_CLAIM_ABOUT_HIDDEN_COGNITION'}


def attest_turn_model(config, session, turn, model, workspace, *, start, end, backend,
                      missing='NATIVE_REVIEW_INCOMPLETE', allow_incomplete=False):
    info = session_record(config, session)
    if info['model'] != model:
        _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'APP_PARENT_MODEL')
    provider = backend if isinstance(backend, str) and backend and '/' not in backend \
        else info['provider']
    if provider != info['provider']:
        _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'APP_PARENT_PROVIDER')
    try:
        messages, _ = turn_parts(config, session, start, end,
                                 allow_incomplete=allow_incomplete)
    except ContractError as error:
        if str(error) == 'NATIVE_NOT_INVOKED':
            raise ContractError(missing) from None
        raise
    if not any(message['type'] == 'assistant' for message in messages):
        raise ContractError(missing)
    assert_model(messages, model=model, provider=provider, effort=info['effort'])
    return info


def collect(request, config, *, as_of, directory=None, timeout_seconds=30,
            require_configured_model=False):
    """Read an exact OpenCode child task and return its verified final reply."""
    from .agent_review import parse_reply, validate_reply, REJECTION_CODES
    from .native_handoff import (runner_review, load_dispatch, packet, verify_submission_window,
        FRESH_SECONDS, CONFIRMED_PAGES, COMPACT_PAGES)
    from .native_identity import assert_parent, under_work
    identity = request.get('native_identity')
    if not isinstance(identity, dict):
        raise ContractError('NATIVE_IDENTITY_UNAVAILABLE')
    if identity.get('provider') != 'opencode' or identity.get('adapter') != SCHEMA:
        raise ContractError('NATIVE_PROVIDER_UNSUPPORTED')
    assert_parent(identity, config, require_configured_model=require_configured_model, as_of=as_of)
    if request.get('model') != identity['model']:
        raise ContractError('NATIVE_REVIEW_REQUEST_HASH')
    if not 0 <= (utc(as_of) - utc(request['as_of_utc'])).total_seconds() <= 600:
        raise ContractError('NATIVE_REQUEST_STALE')
    directory = under_work(directory) if directory is not None else None
    reserved = runner_review(directory)
    inline = bool(request.get('input_transport'))
    if inline and not reserved:
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    if reserved and (utc(as_of) - utc(request['as_of_utc'])).total_seconds() >= FRESH_SECONDS:
        raise ContractError('NATIVE_REQUEST_STALE')
    args, fingerprint, pages = packet(request, directory)
    marker = args['title']; brief = args['brief']
    with read_db(config['openbot_db']) as db:
        rows = db.execute('''SELECT thread_id,created_at FROM projection_agent_threads
          WHERE agent_id=? AND origin='agent' AND title=? AND created_at>=?''',
          (identity['agent_id'], marker, request['as_of_utc'])).fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        thread, created = rows[0]
        if ref(thread) == identity['thread_ref']:
            raise ContractError('NATIVE_SESSION_MISMATCH')
        inputs = db.execute('''SELECT turn_id,message_json FROM projection_thread_messages
          WHERE thread_id=? AND author='agent' AND created_at>=? ORDER BY ordinal''',
          (thread, request['as_of_utc'])).fetchall()
        if not inputs and reserved:
            return None
        if (not inputs or not isinstance(inputs[0][0], str) or not inputs[0][0]
                or json.loads(inputs[0][1]).get('text') != brief):
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        input_turn = inputs[0][0]
        finals = db.execute('''SELECT m.message_json,t.turn_id,t.started_at,t.completed_at,
           p.external_session_id,p.model,p.provider,t.thread_id,p.thread_id,p.effort
          FROM projection_thread_messages m JOIN projection_turns t ON t.turn_id=m.turn_id
          JOIN projection_provider_sessions p ON p.id=t.provider_session_id
          WHERE m.thread_id=? AND m.turn_id=?
          AND m.author='assistant' AND m.item_type='final_answer'
          AND m.status='completed' AND t.status='completed' AND m.created_at>=?
          ORDER BY m.ordinal''', (thread, input_turn, request['as_of_utc'])).fetchall()
        if not finals:
            states = db.execute('SELECT status FROM projection_turns WHERE thread_id=? AND turn_id=?',
                                (thread, input_turn)).fetchall()
            if any(state[0] in {'failed', 'cancelled', 'interrupted'} for state in states):
                raise ContractError('NATIVE_TASK_FAILED')
            return None
        if len(finals) != 1:
            raise ContractError('NATIVE_REVIEW_INCOMPLETE')
    message, turn, start, end, session, session_model, provider, turn_thread, session_thread, session_effort = finals[0]
    if (turn_thread != thread or session_thread != thread
            or ref(session) == identity['external_session_ref']
            or ref(turn) == identity['turn_ref']):
        raise ContractError('NATIVE_SESSION_MISMATCH')
    if provider != identity['provider']:
        _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'APP_CHILD_PROVIDER')
    model = identity['model']
    if require_configured_model and session_model != model:
        _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'APP_CHILD_MODEL')
    if (require_configured_model and identity.get('effort') is not None
            and session_effort != identity['effort']):
        _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'ROLLOUT_SETTINGS_MODEL')
    if not utc(request['as_of_utc']) <= utc(created) <= utc(start) <= utc(end):
        raise ContractError('NATIVE_CHILD_CLOCK_INVALID' if inline else 'AGENT_EVIDENCE_FUTURE')
    if utc(end) > utc(as_of):
        raise ContractError('NATIVE_PROJECTION_AFTER_SNAPSHOT' if inline else 'AGENT_EVIDENCE_FUTURE')
    raw = json.loads(message).get('text')
    if not isinstance(raw, str) or len(raw.encode()) > 32768:
        raise ContractError('AGENT_REPLY_SIZE')
    evidence = None
    submitted = None
    if reserved:
        args, fingerprint, pages, ticket = load_dispatch(directory, request, as_of=as_of)
        submitted = observe_submission(config, identity, request['as_of_utc'], args, as_of=as_of,
            reserved_at=ticket['reserved_at_utc'],
            require_configured_model=require_configured_model)
        verify_submission_window(submitted, ticket)
        if (submitted['submission_state'] != 'ACKNOWLEDGED'
                or submitted['acknowledged_task_ref'] != ref(thread)
                or not utc(ticket['reserved_at_utc']) <= utc(submitted['attempted_at_utc'])
                    <= utc(submitted['responded_at_utc'])
                or not utc(ticket['reserved_at_utc']) <= utc(created)
                    <= utc(submitted['responded_at_utc'])):
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        evidence = (directory, request['material_sha256'], pages)
    else:
        attest_handoff(config, identity, request, as_of=as_of,
                       require_configured_model=require_configured_model)
    proof = attest(config, session, turn, model=model, workspace=config['agent_workspace'],
        start=start, end=end, expected_input=brief, expected_reply=raw,
        backend=identity['provider'], evidence=evidence,
        require_thread_model=require_configured_model,
        effort=identity.get('effort') if require_configured_model else None)
    assert_parent(identity, config, require_configured_model=require_configured_model, as_of=as_of)
    try:
        validated = validate_reply(parse_reply(raw), request)
        validation = {'reply_validation_status': 'VALIDATED', 'validated_rows': validated['accepted']}
    except ContractError as error:
        if str(error) not in REJECTION_CODES:
            raise
        validation = {'reply_validation_status': 'REJECTED',
                      'reply_rejection_reason': str(error), 'validated_rows': 0}
    audit = {'schema_version': 'openbot.native-review.audit.v1',
        'audit_source': 'OPENBOT_APP_SCOPED_READ_ONLY_AUDIT',
        'agent_name': identity['agent_name'], 'model': model, 'provider': provider,
        'agent_id': identity['agent_id'], 'native_identity': identity,
        'skill_sha256': request['skill_sha256'], 'material_sha256': request['material_sha256'],
        'reply_sha256': digest(raw.encode()), 'native_invocation_verified': True,
        'native_app_turns': 1, 'native_started_at_utc': start, 'native_completed_at_utc': end,
        'audited_at_utc': as_of,
        'submission_transport':
            'EXISTING_AGENT_START_TASK; EXACT_PROVIDER_ATTESTED_PAGED_INPUT',
        'authority': 'ADVISORY_ONLY; NO_HOST_ISOLATION_CLAIM',
        'trade_authorization': False, **proof, **validation}
    if reserved:
        audit.update(submission_attempts=submitted['submission_attempts'], task_ref=ref(thread),
            arguments_sha256=ticket['arguments_sha256'], packet_sha256=fingerprint,
            verified_evidence_pages=len(pages))
        if request.get('input_transport') == CONFIRMED_PAGES:
            audit.update(parent_delivery=ticket['parent_delivery'],
                argument_integrity=ticket['argument_integrity'],
                preview_sha256=ticket['preview_sha256'])
        elif request.get('input_transport') == COMPACT_PAGES:
            audit.update(parent_delivery='EXACT_TASK_ARGUMENTS_IN_PROVIDER_RECORD')
    return raw, audit


def attest_start_command(identity, config, state):
    """Find the exact successful runner start command in the parent turn."""
    from .native_identity import assert_current, parent_binding
    from .contracts import now_utc
    from .native_handoff import wsl_root
    assert_current(identity, config)
    binding = parent_binding(identity, config, require_configured_model=True, as_of=now_utc())
    start = _at(binding['started_at'])
    end = _at(binding['completed_at']) if binding['completed_at'] else _at(now_utc())
    messages, parts = turn_parts(config, binding['external'], start, end,
                                 allow_incomplete=binding.get('status') != 'completed')
    assert_model(messages, model=identity['model'], provider=identity['provider'],
                 effort=identity.get('effort'), allow_empty=True)
    root = wsl_root()
    quoted = root.replace("'", "''")
    argv = ['python3', '-m', 'researcher.openbot_runner', 'start', '--request-id',
            state['request_id']]
    allowed = {f"wsl.exe --cd '{quoted}' -- " + ' '.join(argv)}
    if "'" not in root and all(part and part.isascii() and part.isalnum() or part in '/._-'
                               for part in root):
        allowed.add(f'wsl.exe --cd {root} -- ' + ' '.join(argv))
    proof = None
    for part in parts:
        if part['type'] != 'tool' or part['data']['name'] != 'shell':
            continue
        state_data = part['data']['state']
        try:
            _tool_state(part)
        except ContractError:
            continue
        command = state_data['input']['command']
        if command not in allowed:
            continue
        _text_content(state_data['content'])
        if proof is not None:
            raise ContractError('RUNNER_START_UNATTESTED')
        proof = {'status': 'VERIFIED_OPENBOT_AGENT_COMMAND',
            'source': 'OPENCODE_PROVIDER_SHELL_EXECUTION',
            'parent_turn_ref': ref(binding['turn']),
            'command_sha256': digest(command.encode()), 'verified_at_utc': now_utc()}
    if proof is None:
        raise ContractError('RUNNER_START_UNATTESTED')
    return proof


def _attached(arguments, target):
    if not isinstance(arguments, dict) or set(arguments) != {'paths'}:
        return False
    paths = arguments['paths']
    if not isinstance(paths, list) or len(paths) != 1 or not isinstance(paths[0], str):
        return False
    try:
        return (checked_path(paths[0], root=target.parent, error='NATIVE_REPLY_PROVENANCE')
                == checked_path(target, error='NATIVE_REPLY_PROVENANCE'))
    except ContractError:
        return False


def _final_text(parts, message_id):
    selected = [part for part in parts if part['message']['id'] == message_id]
    texts = [part for part in selected if part['type'] == 'text']
    if len(texts) != 1 or not selected or selected[-1] is not texts[0]:
        raise ContractError('NATIVE_REPLY_PROVENANCE')
    return texts[0]['data']['text']


def _delivery_window(messages, bound_end):
    report = None
    for index, message in enumerate(messages):
        if (message['type'] == 'user' and message['moment'] >= bound_end
                and message['data']['text'].startswith('Task report from OpenBot:')):
            report = index
            break
    if report is None:
        return None
    if any(message['type'] == 'user' for message in messages[report + 1:]):
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    final = None
    for index in range(report + 1, len(messages)):
        message = messages[index]
        if message['type'] == 'assistant' and message['data']['finish'] == 'stop':
            final = index
            break
    if final is None:
        return None
    if any(message['type'] == 'assistant' for message in messages[final + 1:]):
        raise ContractError('NATIVE_HANDOFF_UNATTESTED')
    return report, final


def delivery_proof(state, config):
    """Observe the exact parent attachment and final text, without sending."""
    from .native_identity import parent_binding, local_path
    from .contracts import now_utc
    identity = state['native_identity']
    binding = parent_binding(identity, config, require_configured_model=False, as_of=now_utc())
    artifact = state.get('artifact', {})
    if not artifact:
        return None
    target = local_path(artifact['attachment_path'])
    expected = local_path(config['agent_workspace']) / 'market-research-results' / (
        state['job_id'] + '.zip')
    if target != expected:
        raise ContractError('NATIVE_REPLY_PROVENANCE')
    raw_zip = checked_path(target, error='NATIVE_REPLY_PROVENANCE').read_bytes()
    if digest(raw_zip) != artifact['sha256']:
        raise ContractError('NATIVE_REPLY_PROVENANCE')
    from .diagnostic_export import verify_zip
    verify_zip(raw_zip)
    if binding['status'] != 'completed' or not binding['completed_at']:
        return None
    start = _at(binding['started_at'])
    bound_end = _at(binding['completed_at'])
    end = _at(now_utc())
    messages, parts = turn_parts(config, binding['external'], start, end)
    if not any(message['type'] == 'assistant' for message in messages):
        return None
    assert_model(messages, model=identity['model'], provider=identity['provider'],
                 effort=identity.get('effort'), allow_empty=True)
    window = _delivery_window(messages, bound_end)
    if window is None:
        return None
    report_index, final_index = window
    delivery = messages[report_index:final_index + 1]
    assert_model(delivery, model=identity['model'], provider=identity['provider'],
                 effort=identity.get('effort'))
    final = messages[final_index]
    provider_text = _final_text(parts, final['id'])
    if state['job_id'] not in provider_text or artifact['sha256'] not in provider_text:
        return None
    delivery_ids = {message['id'] for message in delivery}
    tool_parts = [part for part in parts
                  if part['message']['id'] in delivery_ids and part['type'] == 'tool']
    exec_calls = {id(part): call for part, call in _execute_parts(tool_parts)}
    attached = 0
    for part in tool_parts:
        if part['data']['name'] == 'shell':
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        call = exec_calls.get(id(part))
        if call is None:
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        state_data = part['data']['state']
        try:
            parsed = parse_execute(state_data['input'].get('code'))
        except ContractError:
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL') from None
        argument = parsed['argument']
        if (parsed['method'] != 'tool_call' or not isinstance(argument, dict)
                or set(argument) != {'name', 'arguments'}
                or argument.get('name') != 'openbot.attach_files_to_response'
                or call['tool'] != 'openbot.tool_call' or call['input'] != argument
                or state_data['status'] != 'completed' or call['status'] != 'completed'
                or not _attached(argument['arguments'], target)):
            raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
        attached += 1
    if attached > 1:
        raise ContractError('NATIVE_UNAUTHORIZED_TOOL')
    size = target.stat().st_size
    with read_db(config['openbot_db']) as db:
        turns = db.execute('''SELECT turn_id,started_at,completed_at FROM projection_turns
          WHERE thread_id=? AND status='completed' ORDER BY started_at''',
          (binding['thread'],)).fetchall()
        matches = []
        for turn, started, completed in turns:
            if _at(started) < bound_end:
                continue
            rows = db.execute('''SELECT author,item_type,status,message_json
              FROM projection_thread_messages WHERE thread_id=? AND turn_id=?
              ORDER BY ordinal''', (binding['thread'], turn)).fetchall()
            finals = [json.loads(raw) for author, item_type, status, raw in rows
                      if author == 'assistant' and item_type == 'final_answer'
                      and status == 'completed']
            if len(finals) == 1 and finals[0].get('text') == provider_text:
                matches.append((turn, started, completed, rows, finals[0]))
        if not matches:
            return None
        if len(matches) != 1:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        turn, started, completed, rows, final_answer = matches[0]
        if not bound_end <= _at(started) <= _at(completed) <= end:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        attachments = final_answer.get('attachments')
        if not isinstance(attachments, list):
            raise ContractError('NATIVE_REPLY_PROVENANCE')
        matched = [a for a in attachments if isinstance(a, dict)
                   and a.get('name') == target.name and a.get('size') == size]
        wrong = [a for a in attachments if isinstance(a, dict)
                 and a.get('name') == target.name and a.get('size') != size]
        if len(matched) != 1 or wrong:
            raise ContractError('NATIVE_REPLY_PROVENANCE')
        exchange = [json.loads(raw) for author, item_type, status, raw in rows
                    if author == 'agent' and item_type == 'agent-exchange'
                    and status == 'completed']
        if len(exchange) != 1:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        exchange = exchange[0]
        child_thread = (exchange.get('exchange') or {}).get('senderTaskId')
        if not isinstance(child_thread, str) or not child_thread:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        child = db.execute('''SELECT title,created_at FROM projection_agent_threads
          WHERE thread_id=?''', (child_thread,)).fetchone()
        if not child:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        title, created = child
        material = state.get('material_sha256')
        if not isinstance(material, str) or title != 'OPENBOT-RESEARCH-' + material:
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        prepared = state.get('request_prepared_at_utc') or state.get('created_at_utc')
        if not isinstance(prepared, str) or utc(created) < utc(prepared):
            raise ContractError('NATIVE_HANDOFF_UNATTESTED')
        child_final = db.execute('''SELECT message_json FROM projection_thread_messages
          WHERE thread_id=? AND author='assistant' AND item_type='final_answer'
          AND status='completed' ORDER BY ordinal''', (child_thread,)).fetchall()
        if (len(child_final) != 1
                or json.loads(child_final[0][0]).get('text') != exchange.get('text')):
            raise ContractError('NATIVE_REPLY_PROVENANCE')
        child_session = db.execute('''SELECT external_session_id,model,provider,effort
          FROM projection_provider_sessions WHERE thread_id=?''', (child_thread,)).fetchall()
        if len(child_session) != 1:
            raise ContractError('NATIVE_SESSION_MISMATCH')
        child_external, child_model, child_provider, child_effort = child_session[0]
        if child_provider != identity['provider'] or child_model != identity['model']:
            _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'APP_CHILD_MODEL')
        if identity.get('effort') is not None and child_effort != identity['effort']:
            _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'ROLLOUT_SETTINGS_MODEL')
        retained = session_record(config, child_external)
        if retained['model'] != identity['model']:
            _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'APP_CHILD_MODEL')
        if identity.get('effort') is not None and retained['effort'] != identity['effort']:
            _fail('NATIVE_MODEL_SWITCHED', 'IDENTITY', 'ROLLOUT_SETTINGS_MODEL')
    return {'status': 'VERIFIED_OPENBOT_FINAL_DELIVERY', 'job_id': state['job_id'],
        'zip_sha256': artifact['sha256'], 'parent_turn_ref': ref(turn),
        'completed_at_utc': completed, 'trade_authorization': False}
