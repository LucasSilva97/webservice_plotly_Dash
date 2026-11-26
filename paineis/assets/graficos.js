// Ponte entre o Dash e o Apache ECharts (echarts.min.js, carregado antes por ordem alfabética).
//
// Cada gráfico é um dcc.Store com a opção do ECharts montada no Python (paineis/comum/graficos.py)
// e um <div id="<id>-area"> onde o gráfico é desenhado. Um callback clientside chama
// graficos.desenhar sempre que a opção muda. A instância do ECharts é reaproveitada entre
// atualizações, então trocar um filtro anima a transição dos dados em vez de redesenhar do zero.
//
// JSON não leva funções: onde a opção traz "fn:<nome>" (formatter, valueFormatter), a ponte troca
// pela função de mesmo nome em FORMATOS. Sempre com guarda de nulo, como no AG Grid.
(function () {
  function numero(valor, opcoes) {
    if (valor === null || valor === undefined || valor === "" || valor === "-" || isNaN(valor)) return "—";
    return new Intl.NumberFormat("pt-BR", opcoes).format(valor);
  }
  function moedaCurta(v) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    var a = Math.abs(v);
    if (a >= 1e6) return "R$ " + numero(v / 1e6, { maximumFractionDigits: 1 }) + " mi";
    if (a >= 1e3) return "R$ " + numero(v / 1e3, { maximumFractionDigits: 0 }) + " mil";
    return "R$ " + numero(v, { maximumFractionDigits: 0 });
  }
  function comSufixo(texto, sufixo) { return texto === "—" ? texto : texto + sufixo; }
  function valorDe(p) { return p && typeof p === "object" && "value" in p ? p.value : p; }

  var FORMATOS = {
    inteiro: function (v) { return numero(valorDe(v), { maximumFractionDigits: 0 }); },
    dec1: function (v) { return numero(valorDe(v), { minimumFractionDigits: 1, maximumFractionDigits: 1 }); },
    moeda: function (v) { return numero(valorDe(v), { style: "currency", currency: "BRL" }); },
    moedaCurta: function (v) { return moedaCurta(valorDe(v)); },
    pct: function (v) { return comSufixo(numero(valorDe(v), { minimumFractionDigits: 1, maximumFractionDigits: 1 }), "%"); },
    pct0: function (v) { return comSufixo(numero(valorDe(v), { maximumFractionDigits: 0 }), "%"); },
  };

  function resolver(no) {
    if (typeof no === "string" && no.indexOf("fn:") === 0) return FORMATOS[no.slice(3)] || no;
    if (Array.isArray(no)) return no.map(resolver);
    if (no && typeof no === "object") {
      var copia = {};
      for (var k in no) if (Object.prototype.hasOwnProperty.call(no, k)) copia[k] = resolver(no[k]);
      return copia;
    }
    return no;
  }

  var instancias = {}; // id da área -> {el, grafico, observador}

  function descartar(id) {
    var r = instancias[id];
    if (!r) return;
    r.observador.disconnect();
    r.grafico.dispose();
    delete instancias[id];
  }

  function instancia(id, el) {
    // Páginas trocadas (Comercial) ou blocos recriados por callback deixam instâncias órfãs.
    for (var outro in instancias) if (!instancias[outro].el.isConnected) descartar(outro);
    var r = instancias[id];
    if (r && r.el !== el) { descartar(id); r = null; }
    if (!r) {
      var grafico = window.echarts.init(el, null, { renderer: "canvas" });
      var observador = new ResizeObserver(function () { grafico.resize({ animation: { duration: 250 } }); });
      observador.observe(el);
      r = instancias[id] = { el: el, grafico: grafico, observador: observador };
    }
    return r.grafico;
  }

  function desenhar(opcao, id, tentativa) {
    var el = document.getElementById(id);
    if (!el || !window.echarts) {
      // O callback pode rodar antes de o React montar o <div>: tenta de novo por até ~2 s.
      if ((tentativa || 0) < 40) setTimeout(function () { desenhar(opcao, id, (tentativa || 0) + 1); }, 50);
      return;
    }
    var grafico = instancia(id, el);
    if (!opcao) { grafico.clear(); return; }
    // replaceMerge: séries que saem da opção somem; as que ficam (mesmo id) animam a transição.
    grafico.setOption(resolver(opcao), { replaceMerge: ["series"] });
  }

  window.dash_clientside = Object.assign({}, window.dash_clientside, {
    graficos: {
      desenhar: function (opcao, id) {
        desenhar(opcao, id);
        return window.dash_clientside.no_update;
      },
    },
  });
})();
