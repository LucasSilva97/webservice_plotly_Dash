// Formatadores pt-BR usados nas colunas do AG Grid ({"function": "moeda(params.value)"}).
// Sempre com guarda de nulo: um erro no formatador congela a grade inteira, sem mensagem.
var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});

function _numero(valor, opcoes) {
  if (valor === null || valor === undefined || valor === "" || isNaN(valor)) return "—";
  return new Intl.NumberFormat("pt-BR", opcoes).format(valor);
}

dagfuncs.inteiro = function (v) { return _numero(v, { maximumFractionDigits: 0 }); };
dagfuncs.dec1 = function (v) { return _numero(v, { minimumFractionDigits: 1, maximumFractionDigits: 1 }); };
dagfuncs.dec2 = function (v) { return _numero(v, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };
dagfuncs.moeda = function (v) { return _numero(v, { style: "currency", currency: "BRL" }); };
dagfuncs.pct = function (v) {
  var texto = _numero(v, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return texto === "—" ? texto : texto + "%";
};
dagfuncs.data = function (v) {
  if (!v) return "—";
  return v.slice(8, 10) + "/" + v.slice(5, 7) + "/" + v.slice(0, 4);
};
dagfuncs.mes = function (v) {
  if (!v) return "—";
  var meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  return meses[(v % 100) - 1] + "/" + String(Math.floor(v / 100)).slice(2);
};
