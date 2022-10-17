# Redis-DoS-Exploit

Redis DoS

Affected version: v2.8-7.0.5 (latest till now)

They think it is not a security problem, so no CVE assigned, and definitely it's safe to disclose the exploit :) 

## Usage
```
python exp.py -h

python exp.py --rhost=127.0.0.1 --lhost 127.0.0.1
```

## Root cause
Function `replicationResurrectCachedMaster` does not check whether `server.cached_master` is NULL. It will lead to NULL pointer dereference when a server sends malformed data during replication. 

## Credit
Code based on @n0b0dyCN (https://github.com/n0b0dyCN/redis-rogue-server)