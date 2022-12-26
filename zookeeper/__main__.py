from argparse import ArgumentParser
from logging import getLogger, basicConfig, INFO
from os import environ
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs
from uuid import UUID

from nginxproxymanager import NginxProxyManagerClient
from pydactyl import PterodactylClient

if TYPE_CHECKING:
    from typing import Any
    from logging import Logger
    from argparse import Namespace
    from requests import Response
    from nginxproxymanager.types import ProxyHostProperties, Location
    from pydactyl.responses import PaginatedResponse  # isn't exposed
    from urllib.parse import ParseResult

logger: "Logger" = getLogger(__name__)


def main() -> None:
    parser: "ArgumentParser" = ArgumentParser(prog="zookeeper")
    # auth requirements
    parser.add_argument(
        "--proxy-token", "-pt",
        dest="proxy_token",
        type=str,
        help="Nginx Proxy Manager API token"
    )
    parser.add_argument(
        "--proxy-url", "-pn",
        dest="proxy_host",
        type=str,
        help="Nginx Proxy Manager host"
    )
    parser.add_argument(
        "--panel-key", "-pk",
        dest="panel_token",
        type=str,
        help="Pterodactyl API key"
    )
    parser.add_argument(
        "--panel-url", "-ph",
        dest="panel_host",
        type=str,
        help="Pterodactyl host"
    )
    # pterodactyl server configuration
    parser.add_argument(
        "--name", "-n",
        dest="name",
        type=str,
        help="Name of the server",
        default="Stingray",
        required=True,
    )
    parser.add_argument(
        "--nest", "-ne",
        dest="nest",
        type=int,
        help="Nest ID",
    )
    parser.add_argument(
        "--egg", "-e",
        dest="egg",
        type=int,
        help="Egg ID",
    )
    parser.add_argument(
        "--location", "-l",
        dest="location",
        type=int,
        help="Location ID",
        default=1,
    )
    parser.add_argument(
        "--memory", "-m",
        dest="memory",
        type=int,
        help="Memory allocation (Megabytes)",
        default=1000,
    )
    parser.add_argument(
        "--swap", "-s",
        dest="swap",
        type=int,
        help="Swap allocation (Megabytes) (-1 for infinite)",
        default=-1,
    )
    parser.add_argument(
        "--cpu", "-c",
        dest="cpu",
        type=int,
        help="CPU allocation (Percentage)",
        default=100,
    )
    parser.add_argument(
        "--disk", "-d",
        dest="disk",
        type=int,
        help="Disk allocation (Megabytes)",
        default=1000,
    )
    parser.add_argument(
        "--user", "-u",
        dest="user",
        type=int,
        help="User ID",
        default=1,
    )
    # proxy server configuration
    parser.add_argument(
        "--proxy", "-p",
        dest="proxy",
        type=int,
        help="Proxy ID",
    )

    args: "Namespace" = parser.parse_args()

    # environment variables
    proxy_token: str | None = args.proxy_token or environ.get("STINGRAY_PROXY_TOKEN")
    if proxy_token is None:
        raise ValueError("Proxy token not provided")

    proxy_host: str | None = args.proxy_host or environ.get("STINGRAY_PROXY_HOST")
    if proxy_host is None:
        raise ValueError("Proxy host not provided")

    panel_token: str | None = args.panel_token or environ.get("STINGRAY_PANEL_TOKEN")
    if panel_token is None:
        raise ValueError("Panel token not provided")

    panel_host: str | None = args.panel_host or environ.get("STINGRAY_PANEL_HOST")
    if panel_host is None:
        raise ValueError("Panel host not provided")

    # setup logging
    basicConfig(level=INFO)

    # init clients
    proxy_client: "NginxProxyManagerClient" = NginxProxyManagerClient(
        host=proxy_host,
        token=proxy_token
    )
    ptero_client: "PterodactylClient" = PterodactylClient(
        url=panel_host,
        api_key=panel_token
    )

    # test clients
    logger.info("Polling proxy...")
    proxy_client.nginx.get_proxy_hosts()
    logger.info("Proxy is online.")

    logger.info("Polling panel...")
    ptero_client.locations.list_locations(includes=("nodes",))
    logger.info("Panel is online.")

    # make server
    server_response: "Response" = ptero_client.servers.create_server(
        name=args.name,
        user_id=args.user,
        nest_id=args.nest,
        egg_id=args.egg,
        memory_limit=args.memory,
        cpu_limit=args.cpu,
        swap_limit=args.swap,
        disk_limit=args.disk,
        location_ids=(args.location,),
    )
    server_response_json: dict[str, str | dict[str, "Any"]] = server_response.json()
    # this library is balls and doesn't have types

    server_uuid_str: str = server_response_json["attributes"]["uuid"]
    server_uuid: "UUID" = UUID(server_uuid_str)
    server_uuid_nodash: str = server_uuid.hex

    server_allocation_id: int = server_response_json["attributes"]["allocation"]
    server_node_id: int = server_response_json["attributes"]["node"]

    logger.info(f"Server successfully created with UUID {server_response.json()['attributes']['uuid']}")

    # get node info to input into proxy
    node_allocations: "PaginatedResponse" = ptero_client.nodes.list_node_allocations(server_node_id)
    node_allocations_json: list["Any"] = node_allocations.collect()

    node_allocation: dict[str, str | int | bool | None] = \
    next(filter(lambda allocation: allocation["attributes"]["id"] == server_allocation_id, node_allocations_json))[
        "attributes"]

    node_allocation_ip: str = node_allocation["alias"] or node_allocation["ip"]
    node_allocation_port: int = node_allocation["port"]
    # These are the public-facing IP and port of the server that we can use to make the proxy host

    # make proxy server
    old_proxy_data: "ProxyHostProperties" = proxy_client.nginx.get_proxy_host(args.proxy)

    old_locations: list["Location"] = old_proxy_data["locations"].copy()
    old_locations.append({
        "path": f"/{server_uuid_nodash}",
        "forward_host": node_allocation_ip,
        "forward_port": node_allocation_port,
        "forward_scheme": "http",
        "advanced_config": "",
    })

    proxy_response: "ProxyHostProperties" = proxy_client.nginx.helper_modify_proxy_host(
        args.proxy,
        locations=old_locations,
    )

    # Finally, assemble the URL for the user to use.
    default_vnc_url: str = "https://novnc.com/noVNC/vnc_lite.html"  # again, no logic so this is the default

    proxied_host: str = proxy_response["domain_names"][0]
    proxied_port: int = 443 if proxy_response["certificate_id"] != "0" else 80
    proxied_path: str = server_uuid_nodash
    password: str = "password"  # No logic here. Use default.

    new_query_arguments: dict = {
        "host": proxied_host,
        "port": proxied_port,
        "path": proxied_path,
        "password": password,
    }

    urlparse_result: "ParseResult" = urlparse(default_vnc_url)

    old_query_arguments: dict = parse_qs(urlparse_result.query)

    query_builder: dict = old_query_arguments.copy()

    query_builder.update(new_query_arguments)

    # our query_builder is now complete

    new_query: str = urlencode(new_query_arguments)

    new_proxy_url: str = urlunparse(urlparse_result._replace(query=new_query))

    logger.info(
        f"Server will be accessible at {new_proxy_url}. Please wait for the server to finish installing before attempting to connect.")


if __name__ == "__main__":
    main()
