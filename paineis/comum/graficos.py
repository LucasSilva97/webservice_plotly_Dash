"""Gráficos com Apache ECharts (paineis/assets/echarts.min.js + graficos.js).

O Python só monta a opção do ECharts (um dict); quem desenha é o navegador. Cada gráfico é um
dcc.Store com a opção e um <div> onde ele é desenhado; um callback clientside liga os dois. Como a
instância do ECharts é reaproveitada, trocar um filtro anima a transição dos dados.

Toda série tem `id`: é por ele que o ECharts casa a série antiga com a nova e anima a diferença.
Funções não passam por JSON; "fn:<nome>" vira o formatador pt-BR de mesmo nome em graficos.js.
"""
import math

from dash import ClientsideFunction, Input, Output, State, dcc, html

AZUL = "#0e4d64"
AZUL_CLARO = "#7fb3c2"
CINZA = "#c9d3d8"
CINZA_ESCURO = "#5d6d75"
CINZA_LINHA = "#9aa8ae"
AMBAR = "#f2a93b"
VERDE_FAIXA = "#cfe8d8"
TRILHO = "#e6ebee"
TEXTO = "#1d2b33"
BORDA = "#dde3e6"

ANIMACAO = {
    "animationDuration": 900, "animationEasing": "cubicOut",
    "animationDurationUpdate": 650, "animationEasingUpdate": "cubicInOut",
}
TOOLTIP_EIXO = {"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}}
LEGENDA = {"bottom": 0, "icon": "roundRect", "itemWidth": 14, "itemHeight": 8, "textStyle": {"color": CINZA_ESCURO}}
ROTULO_EIXO = {"color": CINZA_ESCURO, "fontSize": 11}
LINHA_GRADE = {"lineStyle": {"color": "#edf0f2"}}


def grafico(id, altura=300, opcao=None):
    """Componente do gráfico. `opcao` serve aos gráficos criados dentro de um callback."""
    return html.Div(className="grafico", children=[
        dcc.Store(id=id, data=opcao),
        html.Div(id=f"{id}-area", className="grafico-area", style={"height": f"{altura}px"}),
    ])


def registrar(app, *ids):
    """Liga cada Store ao desenho no navegador. A saída é fictícia: o JS devolve no_update."""
    for id in ids:
        app.clientside_callback(ClientsideFunction("graficos", "desenhar"),
                                Output(f"{id}-area", "className"), Input(id, "data"), State(f"{id}-area", "id"))


def valores(serie):
    """Lista JSON-segura: NaN e None viram null (o ECharts deixa o ponto vazio)."""
    saida = []
    for v in serie:
        try:
            numero = float(v)
        except (TypeError, ValueError):  # None, pd.NA
            numero = math.nan
        saida.append(None if math.isnan(numero) else numero)
    return saida


def opcao(**partes):
    """Opção base (fonte, animação, cores) mais as partes do gráfico."""
    return {"textStyle": {"fontFamily": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif", "color": TEXTO},
            **ANIMACAO, **partes}


def eixo_valor(formato="inteiro", **extra):
    return {"type": "value", "axisLabel": {**ROTULO_EIXO, "formatter": f"fn:{formato}"}, "splitLine": LINHA_GRADE, **extra}


def eixo_categoria(categorias, **extra):
    return {"type": "category", "data": list(categorias), "axisLabel": ROTULO_EIXO,
            "axisTick": {"show": False}, "axisLine": {"lineStyle": {"color": BORDA}}, **extra}


def barras(id, nome, dados, cor=None, horizontal=False, **extra):
    """Série de barras com a ponta arredondada (só o lado de fora). Sem `cor`, cada item traz a sua."""
    estilo = {"borderRadius": [0, 3, 3, 0] if horizontal else [3, 3, 0, 0], **({"color": cor} if cor else {})}
    return {"id": id, "name": nome, "type": "bar", "data": dados, "itemStyle": estilo,
            "emphasis": {"focus": "series"}, "barMaxWidth": 28, **extra}


def gauge(valor, maximo, faixa_verde, formato="dec1", divisoes=4):
    """Velocímetro de meia-volta: trilho cinza com a faixa saudável em verde e ponteiro animado."""
    inicio, fim = faixa_verde[0] / maximo, faixa_verde[1] / maximo
    return opcao(series=[{
        "id": "gauge", "type": "gauge", "min": 0, "max": maximo, "startAngle": 200, "endAngle": -20,
        "center": ["50%", "58%"], "radius": "92%", "splitNumber": divisoes,
        "axisLine": {"roundCap": True, "lineStyle": {"width": 14, "color": [[inicio, TRILHO], [fim, VERDE_FAIXA], [1, TRILHO]]}},
        "progress": {"show": True, "width": 6, "roundCap": True, "itemStyle": {"color": AZUL}},
        "pointer": {"icon": "path://M2,0 L4,0 L5,100 L1,100 Z", "length": "62%", "width": 6, "offsetCenter": [0, 0],
                    "itemStyle": {"color": AZUL}},
        "anchor": {"show": True, "size": 12, "itemStyle": {"color": AZUL, "borderColor": "#fff", "borderWidth": 2}},
        "axisTick": {"show": False},
        "splitLine": {"distance": -14, "length": 14, "lineStyle": {"color": "#fff", "width": 2}},
        "axisLabel": {"distance": 18, "color": CINZA_ESCURO, "fontSize": 10, "formatter": "fn:inteiro"},
        "title": {"show": False},
        "detail": {"valueAnimation": True, "offsetCenter": [0, "62%"], "fontSize": 28, "fontWeight": 600,
                   "color": TEXTO, "formatter": f"fn:{formato}"},
        "data": [{"value": valores([valor])[0] or 0}],
    }])
