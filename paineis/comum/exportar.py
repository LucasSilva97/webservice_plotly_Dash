"""Exportação para Excel: a tabela como está na tela + uma aba com os filtros aplicados."""
import io
from datetime import datetime

import pandas as pd
from openpyxl.styles import Font, PatternFill

COR_CABECALHO = "0E4D64"


def tabela_da_grade(linhas, colunas):
    """Linhas do AG Grid (virtualRowData: já filtradas e ordenadas) com os títulos da tela."""
    campos = [c["field"] for c in colunas if c.get("field") and not c.get("hide")]
    df = pd.DataFrame(linhas or [], columns=campos)
    return df.rename(columns={c["field"]: c.get("headerName", c["field"]) for c in colunas if c.get("field")})


def planilha(abas, filtros):
    """abas: {nome: DataFrame}; filtros: lista de (rótulo, valor). Devolve os bytes do .xlsx."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        for nome, df in abas.items():
            df.to_excel(escritor, sheet_name=nome[:31], index=False)
            folha = escritor.sheets[nome[:31]]
            for celula in folha[1]:
                celula.font = Font(bold=True, color="FFFFFF")
                celula.fill = PatternFill("solid", fgColor=COR_CABECALHO)
            for i, coluna in enumerate(df.columns, start=1):
                largura = max([len(str(coluna))] + [len(str(v)) for v in df[coluna].head(200)])
                folha.column_dimensions[folha.cell(1, i).column_letter].width = min(max(largura + 2, 9), 45)
            folha.freeze_panes = "A2"
            folha.auto_filter.ref = folha.dimensions
        info = list(filtros) + [("Exportado em", datetime.now().strftime("%d/%m/%Y %H:%M"))]
        pd.DataFrame(info, columns=["Filtro", "Valor"]).to_excel(escritor, sheet_name="Filtros", index=False)
    return buffer.getvalue()


def texto_filtro(valor):
    if valor in (None, [], ""):
        return "todos"
    return "; ".join(str(v) for v in valor) if isinstance(valor, list) else str(valor)
