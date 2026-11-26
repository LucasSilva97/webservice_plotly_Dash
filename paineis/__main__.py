"""Abre os painéis: python -m paineis [--porta 8050] [--host 0.0.0.0] [--abrir]

Os três painéis rodam num único servidor waitress. Por padrão ele escuta em 0.0.0.0 (todas as
interfaces): outra pessoa na mesma rede abre pelo IP desta máquina. --host 127.0.0.1 restringe a
esta máquina. Ctrl+C encerra.
"""
import argparse
import socket
import webbrowser

from waitress import serve

from paineis.comum import dados
from paineis.servidor import criar_servidor


def ip_na_rede():
    """IP desta máquina na rede local: o da interface da rota padrão. connect() em UDP só escolhe
    a rota, não envia nada. None se não houver rede."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except OSError:
            return None
    return None if ip.startswith(("0.", "127.")) else ip


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m paineis")
    parser.add_argument("--porta", type=int, default=8050)
    parser.add_argument("--host", default="0.0.0.0",
                        help="interface em que o servidor escuta (padrão 0.0.0.0, toda a rede; 127.0.0.1 = só esta máquina)")
    parser.add_argument("--abrir", action="store_true", help="abre o navegador na página inicial")
    args = parser.parse_args(argv)

    if not (dados.PASTA_PUBLICADO / "_manifesto.json").exists():
        raise SystemExit("Nenhum dado publicado. Rode o ELT antes: python -m elt")
    local = f"http://127.0.0.1:{args.porta}/"
    print(f"Painéis (estoque/, comercial/, credito/) — Ctrl+C para encerrar\n  nesta máquina: {local}")
    if args.host == "0.0.0.0":
        ip = ip_na_rede()
        if ip:
            print(f"  na rede:       http://{ip}:{args.porta}/   (para outras pessoas na mesma rede)")
        else:
            print("  na rede:       sem rede detectada; quem estiver na mesma rede usa o IP desta máquina")
    elif not args.host.startswith("127."):
        print(f"  na rede:       http://{args.host}:{args.porta}/")
    if args.abrir:
        webbrowser.open(local)
    serve(criar_servidor(), host=args.host, port=args.porta, threads=8)


# if __name__ == "__main__":
#     main()
