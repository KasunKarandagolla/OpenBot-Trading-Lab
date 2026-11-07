"""Windows-native launcher for the bounded WSL worker, using argument arrays."""
import argparse
import os
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout-wsl',required=True)
    parser.add_argument('--cache-wsl',required=True)
    parser.add_argument('--shared',type=Path,required=True)
    parser.add_argument('--distribution',default='Ubuntu-24.04')
    parser.add_argument('--max-seconds',type=int,default=300)
    args=parser.parse_args()
    if os.name!='nt' or not 1<=args.max_seconds<=3600:
        parser.error('Run with native Windows Python; worker duration must be 1..3600 seconds')
    shared=args.shared.resolve(strict=True)
    if shared.name!='Shared' or shared.parent.name!='OpenBot' or not shared.is_dir():
        parser.error('Use the discovered Windows OpenBot Shared directory')
    for value in [args.checkout_wsl,args.cache_wsl,str(shared),args.distribution]:
        if any(c in value for c in '\r\n\x00'):
            parser.error('Invalid path/distribution')
    # Pass arguments directly. Do not evaluate a command string or change script policies.
    prefix=['wsl.exe','-d',args.distribution,'--exec']
    converted=subprocess.run([*prefix,'wslpath','-a','-u',str(shared)],capture_output=True,text=True,check=True)
    command=[*prefix,'bash',args.checkout_wsl.rstrip('/')+'/scripts/lab-shared-worker.sh',
             args.cache_wsl,converted.stdout.strip(),str(args.max_seconds)]
    return subprocess.run(command,check=False).returncode


if __name__=='__main__':raise SystemExit(main())
