# windtunnel
UDP repeater over TCP socket connections

Based on https://stackoverflow.com/questions/3670127/python-socketserver-sending-to-multiple-clients

## Running via docker
### Server mode
```
docker pull jaltieri/windtunnel
docker run --network="host" jaltieri/windtunnel server
```
See additional arguments below

### Client mode
```
docker pull jaltieri/windtunnel
docker run --network="host" jaltieri/windtunnel client localhost
```
See additional arguments below

### Build local docker image
```
docker build . -t jaltieri/windtunnel
```

## Directly running on host
### Server mode
```
usage: windtunnel.py server [-h] [--tcp_server_bind_host TCP_SERVER_BIND_HOST]
                            [--tcp_server_port TCP_SERVER_PORT]
                            [--udp_listen_port UDP_LISTEN_PORT]

optional arguments:
  -h, --help            show this help message and exit
  --tcp_server_bind_host TCP_SERVER_BIND_HOST, -s TCP_SERVER_BIND_HOST
                        host to bind server to, default to 0.0.0.0
  --tcp_server_port TCP_SERVER_PORT, -t TCP_SERVER_PORT
                        port to accept TCP connections from clients on,
                        default to 12321
  --udp_listen_port UDP_LISTEN_PORT, -u UDP_LISTEN_PORT
                        port on which to listen for wind UDP datagrams,
                        default to 5005
```

### Client mode
```
usage: windtunnel.py client [-h] [--port PORT]
                            [--udp_repeater_port UDP_REPEATER_PORT]
                            host

positional arguments:
  host                  host of windtunnel server to connect to

optional arguments:
  -h, --help            show this help message and exit
  --port PORT, -p PORT  port of windtunnel server to connect to, default to
                        12321
  --udp_repeater_port UDP_REPEATER_PORT, -u UDP_REPEATER_PORT
                        port to send repeated UDP datagrams to, default to
                        11111
```
