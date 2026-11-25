"""Chama callbacks Dash pelo HTTP (POST /_dash-update-component), como o navegador faz."""
import base64
import io

import openpyxl


class Grupo:
    """Valores de um grupo ALL: lista de (id concreto, valor)."""

    def __init__(self, itens):
        self.itens = list(itens)


def _item(dependencia, valor):
    if isinstance(valor, Grupo):
        return [{"id": i, "property": dependencia["property"], "value": v} for i, v in valor.itens]
    return {"id": dependencia["id"], "property": dependencia["property"], "value": valor}


def chamar(cliente, prefixo, app, saida, entradas, estados=(), saidas_grupo=None, disparo=None):
    """Executa o callback registrado com a chave `saida` e devolve o dicionário `response`.

    saidas_grupo: {texto do id ALL: [ids concretos]} para as saídas em grupo.
    """
    registro = app.callback_map[saida]
    partes = saida.strip(".").split("...") if saida.startswith("..") else [saida]
    saidas = []
    for parte in partes:
        id_, propriedade = parte.rsplit(".", 1)
        if saidas_grupo and id_ in saidas_grupo:
            saidas.append([{"id": i, "property": propriedade} for i in saidas_grupo[id_]])
        else:
            saidas.append({"id": id_, "property": propriedade})
    corpo = {
        "output": saida,
        "outputs": saidas if len(saidas) > 1 else saidas[0],
        "inputs": [_item(d, v) for d, v in zip(registro["inputs"], entradas)],
        "state": [_item(d, v) for d, v in zip(registro.get("state", []), estados)],
        "changedPropIds": [disparo] if disparo else [],
    }
    resposta = cliente.post(f"{prefixo}_dash-update-component", json=corpo)
    assert resposta.status_code in (200, 204), resposta.get_data(as_text=True)[:2000]
    return resposta.get_json()["response"] if resposta.status_code == 200 else {}


def chave(app, inicio):
    """A chave registrada do callback cuja saída começa com `inicio` (evita repetir o texto inteiro)."""
    encontradas = [k for k in app.callback_map if k.lstrip(".").startswith(inicio)]
    assert len(encontradas) == 1, encontradas
    return encontradas[0]


def ler_xlsx(download):
    """Abre o .xlsx devolvido por um dcc.Download (vem em base64 na resposta)."""
    conteudo = base64.b64decode(download["content"]) if download.get("base64") else download["content"].encode()
    return openpyxl.load_workbook(io.BytesIO(conteudo))
