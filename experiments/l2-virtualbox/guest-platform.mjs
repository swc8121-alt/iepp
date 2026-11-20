import {posix,win32} from 'node:path';

export function resolveGuestPlatform({machineInfo,requested='auto',guestUser,nodeOverride,workdirOverride}){
 const declared=(/^ostype="([^"]+)"/mi.exec(machineInfo)||/^GuestOSType="([^"]+)"/mi.exec(machineInfo)||[])[1]||'';
 const detected=/ubuntu|debian|linux/i.test(declared)?'linux':/windows/i.test(declared)?'windows':null;
 const guestOs=requested==='auto'?detected:requested;
 if(!['linux','windows'].includes(guestOs))throw Error(`Unable to detect guest OS from VirtualBox type '${declared||'unknown'}'. Re-run with --guest-os linux or --guest-os windows.`);
 if(guestOs==='linux'&&!workdirOverride&&!/^[a-z_][a-z0-9_-]*[$]?$/i.test(guestUser))throw Error('Linux guest account contains unsupported path characters. Supply --guest-workdir explicitly.');
 const paths=guestOs==='linux'?posix:win32;
 const guestNode=nodeOverride||(guestOs==='linux'?'/usr/bin/node':'C:\\Program Files\\nodejs\\node.exe');
 const guestWorkdir=workdirOverride||(guestOs==='linux'?`/home/${guestUser}/IEPP-L2`:'C:\\IEPP-L2');
 return {
  declaredType:declared,
  guestOs,
  guestNode,
  guestWorkdir,
  guestState:paths.join(guestWorkdir,'guest-state.json'),
  guestProbe:paths.join(guestWorkdir,'guest-probe.mjs'),
 };
}
