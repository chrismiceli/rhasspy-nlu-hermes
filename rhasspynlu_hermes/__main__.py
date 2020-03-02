"""Hermes MQTT service for rhasspynlu"""
import argparse
import logging
import typing
from pathlib import Path

import paho.mqtt.client as mqtt

from . import NluHermesMqtt

_LOGGER = logging.getLogger(__name__)


def main():
    """Main method."""
    parser = argparse.ArgumentParser(prog="rhasspy-nlu-hermes")
    parser.add_argument("--intent-graph", help="Path to rhasspy intent graph JSON file")
    parser.add_argument(
        "--write-graph",
        action="store_true",
        help="Write training graph to intent-graph path",
    )
    parser.add_argument(
        "--casing",
        choices=["upper", "lower", "ignore"],
        default="ignore",
        help="Case transformation for input text (default: ignore)",
    )
    parser.add_argument(
        "--no-fuzzy", action="store_true", help="Disable fuzzy matching in graph search"
    )
    parser.add_argument(
        "--replace-numbers",
        action="store_true",
        help="Replace digits with words in queries (75 -> seventy five)",
    )
    parser.add_argument(
        "--language", help="Language/locale used for number replacement (default: en)"
    )
    parser.add_argument(
        "--host", default="localhost", help="MQTT host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=1883, help="MQTT port (default: 1883)"
    )
    parser.add_argument(
        "--siteId",
        action="append",
        help="Hermes siteId(s) to listen for (default: all)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to the console"
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    _LOGGER.debug(args)

    try:
        # Convert to Paths
        if args.intent_graph:
            args.intent_graph = Path(args.intent_graph)

        # Listen for messages
        client = mqtt.Client()
        hermes = NluHermesMqtt(
            client,
            graph_path=args.intent_graph,
            write_graph=args.write_graph,
            word_transform=get_word_transform(args.casing),
            replace_numbers=args.replace_numbers,
            language=args.language,
            fuzzy=(not args.no_fuzzy),
            siteIds=args.siteId,
        )

        def on_disconnect(client, userdata, flags, rc):
            try:
                # Automatically reconnect
                _LOGGER.info("Disconnected. Trying to reconnect...")
                client.reconnect()
            except Exception:
                logging.exception("on_disconnect")

        # Connect
        client.on_connect = hermes.on_connect
        client.on_disconnect = on_disconnect
        client.on_message = hermes.on_message

        _LOGGER.debug("Connecting to %s:%s", args.host, args.port)
        client.connect(args.host, args.port)

        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _LOGGER.debug("Shutting down")


# -----------------------------------------------------------------------------


def get_word_transform(name: str) -> typing.Callable[[str], str]:
    """Gets a word transformation function by name."""
    if name == "upper":
        return str.upper

    if name == "lower":
        return str.lower

    return lambda s: s


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
