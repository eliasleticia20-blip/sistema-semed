/**
 * SEMED | Agendamento da Sala de Reuniões - API em Google Apps Script
 *
 * Todas as regras que protegem os dados ficam aqui: a checagem de conflito
 * acontece dentro de uma trava, então dois pedidos simultâneos nunca geram
 * reserva duplicada.
 *
 * Propriedades do script (Configurações do projeto > Propriedades do script):
 *   API_TOKEN       obrigatória. Mesmo valor de API_TOKEN no secrets.toml do app.
 *   SPREADSHEET_ID  só se o script NÃO tiver sido criado dentro da planilha.
 *   SHEET_NAME      opcional. Nome da aba; sem ela, usa a primeira aba.
 */

var VERSAO_API = 2;
var FUSO = 'America/Sao_Paulo';
var HORA_ABERTURA = '07:00';   // manter igual a HORA_ABERTURA em nucleo.py
var HORA_FECHAMENTO = '20:00'; // manter igual a HORA_FECHAMENTO em nucleo.py
var SALA = 'Sala de Reuniões da Secretaria';
var LIMITES = { responsavel: 100, motivo: 500, observacoes: 500 };

var COLUNAS = ['ID', 'Responsavel', 'Data', 'Hora_Inicio', 'Hora_Termino', 'Sala', 'Data_Show', 'Motivo',
  'Observacoes', 'Status', 'Codigo_Cancelamento', 'Criado_Em', 'Cancelado_Em', 'Cancelado_Por'];
var ESSENCIAIS = ['Responsavel', 'Data', 'Hora_Inicio', 'Hora_Termino'];
var APELIDOS = {
  nome: 'Responsavel', nomedoresponsavel: 'Responsavel',
  datadareuniao: 'Data',
  horainicio: 'Hora_Inicio', horariodeinicio: 'Hora_Inicio', inicio: 'Hora_Inicio',
  horatermino: 'Hora_Termino', horaternibi: 'Hora_Termino', horariodetermino: 'Hora_Termino', termino: 'Hora_Termino',
  datashow: 'Data_Show', precisadedatashow: 'Data_Show', solicitoudatashow: 'Data_Show', usardatashow: 'Data_Show',
  motivodareuniao: 'Motivo', observacao: 'Observacoes'
};

function ErroApi(codigo, mensagem) {
  this.codigo = codigo;
  this.mensagem = mensagem;
}

function doGet(e) {
  return responder(function () {
    autorizar((e && e.parameter && e.parameter.token) || '');
    var acao = (e && e.parameter && e.parameter.acao) || 'listar';
    if (acao !== 'listar') throw new ErroApi('VALIDACAO', 'Ação desconhecida.');
    return comTrava(function () {
      var tabela = abrirTabela();
      var linhas = lerLinhas(tabela);
      var reservas = [];
      var invalidas = 0;
      linhas.forEach(function (l) {
        if (l.status === 'cancelada') return;
        if (!l.data || !l.inicio || !l.fim) invalidas++;
        if (!l.data) return;
        reservas.push({
          id: l.id, responsavel: l.responsavel, data: l.data, inicio: l.inicio, fim: l.fim, sala: l.sala,
          data_show: l.dataShow, motivo: l.motivo, observacoes: l.observacoes, tem_codigo: !!l.codigo
        });
      });
      return { reservas: reservas, invalidas: invalidas };
    });
  });
}

function doPost(e) {
  return responder(function () {
    var corpo;
    try {
      corpo = JSON.parse(e.postData.contents);
    } catch (err) {
      throw new ErroApi('VALIDACAO', 'Pedido inválido.');
    }
    autorizar(corpo.token || '');
    if (corpo.acao === 'criar') return comTrava(function () { return criar(corpo); });
    if (corpo.acao === 'cancelar') return comTrava(function () { return cancelar(corpo); });
    throw new ErroApi('VALIDACAO', 'Ação desconhecida.');
  });
}

function criar(p) {
  var responsavel = texto(p.responsavel);
  var motivo = texto(p.motivo);
  var observacoes = texto(p.observacoes);
  if (!responsavel || !motivo) throw new ErroApi('VALIDACAO', 'Informe o responsável e o motivo.');
  if (responsavel.length > LIMITES.responsavel || motivo.length > LIMITES.motivo || observacoes.length > LIMITES.observacoes) {
    throw new ErroApi('VALIDACAO', 'Um dos textos passou do tamanho permitido.');
  }
  if (typeof p.data_show !== 'boolean') throw new ErroApi('VALIDACAO', 'Informe se vai precisar de data show.');

  var data = lerData(p.data);
  var inicio = lerHora(p.inicio);
  var fim = lerHora(p.fim);
  if (!data || !inicio || !fim || String(p.data).length !== 10) throw new ErroApi('VALIDACAO', 'Data ou horário inválido.');
  var a = minutos(inicio);
  var b = minutos(fim);
  if (a >= b) throw new ErroApi('VALIDACAO', 'O término deve ser depois do início.');
  if (a < minutos(HORA_ABERTURA) || b > minutos(HORA_FECHAMENTO)) {
    throw new ErroApi('VALIDACAO', 'A sala funciona das ' + HORA_ABERTURA + ' às ' + HORA_FECHAMENTO + '.');
  }
  var agora = new Date();
  var hoje = Utilities.formatDate(agora, FUSO, 'yyyy-MM-dd');
  var agoraHora = Utilities.formatDate(agora, FUSO, 'HH:mm');
  if (data < hoje || (data === hoje && a < minutos(agoraHora))) {
    throw new ErroApi('VALIDACAO', 'Esse horário já passou.');
  }

  var tabela = abrirTabela();
  var conflito = lerLinhas(tabela).filter(function (l) {
    return l.status !== 'cancelada' && l.data === data && l.inicio && l.fim &&
      Math.max(a, minutos(l.inicio)) < Math.min(b, minutos(l.fim));
  })[0];
  if (conflito) {
    throw new ErroApi('CONFLITO', 'A sala acabou de ser reservada das ' + conflito.inicio + ' às ' + conflito.fim + '.');
  }

  var id = Utilities.getUuid();
  var codigo = Utilities.getUuid().replace(/-/g, '').slice(0, 6).toUpperCase();
  var valores = {
    ID: id, Responsavel: responsavel, Data: data, Hora_Inicio: inicio, Hora_Termino: fim, Sala: SALA,
    Data_Show: p.data_show ? 'Sim' : 'Não', Motivo: motivo, Observacoes: observacoes, Status: 'Ativa',
    Codigo_Cancelamento: codigo, Criado_Em: Utilities.formatDate(agora, FUSO, 'yyyy-MM-dd HH:mm:ss')
  };
  // O apóstrofo guarda tudo como texto e impede que a planilha execute fórmulas digitadas.
  var linha = tabela.cabecalho.map(function (_, i) {
    var v = valores[tabela.nomePorIndice[i]];
    return v === undefined || v === '' ? '' : "'" + v;
  });
  tabela.aba.appendRow(linha);
  SpreadsheetApp.flush();
  return { id: id, codigo: codigo };
}

function cancelar(p) {
  var id = texto(p.id);
  if (!id) throw new ErroApi('VALIDACAO', 'Reserva não informada.');
  var tabela = abrirTabela();
  var alvo = lerLinhas(tabela).filter(function (l) { return l.id === id; })[0];
  if (!alvo || alvo.status === 'cancelada') throw new ErroApi('NAO_ENCONTRADA', 'Essa reserva não existe ou já foi cancelada.');
  var admin = p.admin === true;
  if (!admin) {
    var codigo = texto(p.codigo).toUpperCase();
    if (!codigo || !alvo.codigo || codigo !== alvo.codigo.toUpperCase()) {
      throw new ErroApi('CODIGO_INVALIDO', 'Código de cancelamento incorreto.');
    }
  }
  var agora = Utilities.formatDate(new Date(), FUSO, 'yyyy-MM-dd HH:mm:ss');
  escrever(tabela, alvo.linha, 'Status', 'Cancelada');
  escrever(tabela, alvo.linha, 'Cancelado_Em', agora);
  escrever(tabela, alvo.linha, 'Cancelado_Por', admin ? 'Administrador' : 'Responsável (código)');
  SpreadsheetApp.flush();
  return { id: id };
}

/* ---------- Planilha ---------- */

function abrirTabela() {
  var props = PropertiesService.getScriptProperties();
  var idPlanilha = props.getProperty('SPREADSHEET_ID');
  var planilha = idPlanilha ? SpreadsheetApp.openById(idPlanilha) : SpreadsheetApp.getActiveSpreadsheet();
  if (!planilha) throw new ErroApi('NAO_CONFIGURADO', 'Defina a propriedade SPREADSHEET_ID no Apps Script.');
  var nomeAba = props.getProperty('SHEET_NAME');
  var aba = nomeAba ? planilha.getSheetByName(nomeAba) : planilha.getSheets()[0];
  if (!aba) throw new ErroApi('NAO_CONFIGURADO', 'A aba "' + nomeAba + '" não foi encontrada.');

  var tabela = { aba: aba, fuso: planilha.getSpreadsheetTimeZone() };
  if (aba.getLastRow() === 0) {
    aba.appendRow(COLUNAS);
    SpreadsheetApp.flush();
  }
  mapearCabecalho(tabela);

  var faltando = ESSENCIAIS.filter(function (n) { return tabela.indice[n] === undefined; });
  if (faltando.length) {
    // Nunca seguir sem essas colunas: as reservas sumiriam e a checagem de conflito deixaria tudo passar.
    throw new ErroApi('ESTRUTURA', 'Coluna(s) não encontrada(s) na planilha: ' + faltando.join(', ') + '.');
  }
  var novas = COLUNAS.filter(function (n) { return tabela.indice[n] === undefined; });
  if (novas.length) {
    if (aba.getMaxColumns() < aba.getLastColumn() + novas.length) {
      aba.insertColumnsAfter(aba.getMaxColumns(), novas.length);
    }
    aba.getRange(1, aba.getLastColumn() + 1, 1, novas.length).setValues([novas]);
    SpreadsheetApp.flush();
    mapearCabecalho(tabela);
  }
  completarIds(tabela);
  return tabela;
}

function mapearCabecalho(tabela) {
  var aba = tabela.aba;
  tabela.cabecalho = aba.getRange(1, 1, 1, aba.getLastColumn()).getValues()[0];
  tabela.indice = {};
  tabela.nomePorIndice = {};
  var porChave = {};
  COLUNAS.forEach(function (n) { porChave[chave(n)] = n; });
  tabela.cabecalho.forEach(function (titulo, i) {
    var k = chave(titulo);
    var nome = porChave[k] || APELIDOS[k];
    if (nome && tabela.indice[nome] === undefined) {
      tabela.indice[nome] = i;
      tabela.nomePorIndice[i] = nome;
    }
  });
}

function completarIds(tabela) {
  var aba = tabela.aba;
  var total = aba.getLastRow() - 1;
  if (total < 1) return;
  var faixa = aba.getRange(2, tabela.indice.ID + 1, total, 1);
  var ids = faixa.getValues();
  var mudou = false;
  ids.forEach(function (l) {
    if (!String(l[0]).trim()) {
      l[0] = Utilities.getUuid();
      mudou = true;
    }
  });
  if (mudou) {
    faixa.setValues(ids);
    SpreadsheetApp.flush();
  }
}

function lerLinhas(tabela) {
  var aba = tabela.aba;
  var total = aba.getLastRow() - 1;
  if (total < 1) return [];
  var largura = tabela.cabecalho.length;
  var faixa = aba.getRange(2, 1, total, largura);
  var valores = faixa.getValues();
  var exibidos = faixa.getDisplayValues();
  var idx = tabela.indice;
  function celula(matriz, i, nome) {
    return idx[nome] === undefined ? '' : matriz[i][idx[nome]];
  }
  var linhas = [];
  for (var i = 0; i < total; i++) {
    var responsavel = limparTexto(celula(valores, i, 'Responsavel'));
    var bruto = celula(valores, i, 'Data');
    if (!responsavel && !String(bruto).trim()) continue;
    linhas.push({
      linha: i + 2,
      id: limparTexto(celula(valores, i, 'ID')),
      responsavel: responsavel,
      data: lerData(bruto, tabela.fuso),
      // A hora vem do texto exibido: células de tempo do Sheets chegariam deslocadas no JSON.
      inicio: lerHora(celula(exibidos, i, 'Hora_Inicio')),
      fim: lerHora(celula(exibidos, i, 'Hora_Termino')),
      sala: limparTexto(celula(valores, i, 'Sala')) || SALA,
      dataShow: lerDataShow(celula(valores, i, 'Data_Show')),
      motivo: limparTexto(celula(valores, i, 'Motivo')),
      observacoes: limparTexto(celula(valores, i, 'Observacoes')),
      status: chave(celula(valores, i, 'Status')) === 'cancelada' ? 'cancelada' : 'ativa',
      codigo: limparTexto(celula(valores, i, 'Codigo_Cancelamento'))
    });
  }
  return linhas;
}

function escrever(tabela, linha, nome, valor) {
  tabela.aba.getRange(linha, tabela.indice[nome] + 1).setValue("'" + valor);
}

/* ---------- Conversões ---------- */

function chave(v) {
  return String(v === null || v === undefined ? '' : v).normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^a-z0-9]/g, '');
}

function limparTexto(v) {
  return String(v === null || v === undefined ? '' : v).trim().replace(/^'+/, '').trim();
}

function texto(v) {
  return typeof v === 'string' ? v.trim() : '';
}

function ehData(v) {
  return Object.prototype.toString.call(v) === '[object Date]' && !isNaN(v.getTime());
}

function lerData(v, fuso) {
  if (ehData(v)) return Utilities.formatDate(v, fuso || FUSO, 'yyyy-MM-dd');
  var s = limparTexto(v);
  var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return validarData(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return validarData(+m[3], +m[2], +m[1]);
  return '';
}

function validarData(a, m, d) {
  var dt = new Date(Date.UTC(a, m - 1, d));
  if (dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return '';
  return a + '-' + dois(m) + '-' + dois(d);
}

function lerHora(v) {
  var s = limparTexto(v);
  var m = s.match(/(\d{1,2}):(\d{2})(?::\d{2})?(?:\.\d+)?\s*([AaPp])?/);
  if (!m) return '';
  var h = +m[1];
  var min = +m[2];
  if (m[3]) {
    var pm = m[3].toLowerCase() === 'p';
    if (h === 12) h = pm ? 12 : 0;
    else if (pm) h += 12;
  }
  if (h > 23 || min > 59) return '';
  return dois(h) + ':' + dois(min);
}

function lerDataShow(v) {
  if (v === true) return true;
  var k = chave(v);
  return ['sim', 's', 'yes', 'true', 'verdadeiro', '1', 'comdatashow', 'solicitado', 'necessita', 'precisa'].indexOf(k) >= 0;
}

function minutos(h) {
  var p = h.split(':');
  return +p[0] * 60 + +p[1];
}

function dois(n) {
  return (n < 10 ? '0' : '') + n;
}

/* ---------- Infraestrutura ---------- */

function autorizar(token) {
  var esperado = PropertiesService.getScriptProperties().getProperty('API_TOKEN');
  if (!esperado) throw new ErroApi('NAO_CONFIGURADO', 'Defina a propriedade API_TOKEN no Apps Script.');
  if (token !== esperado) throw new ErroApi('NAO_AUTORIZADO', 'Acesso não autorizado.');
}

function comTrava(fn) {
  var trava = LockService.getScriptLock();
  if (!trava.tryLock(20000)) throw new ErroApi('OCUPADO', 'Sistema ocupado. Tente novamente em instantes.');
  try {
    return fn();
  } finally {
    trava.releaseLock();
  }
}

function responder(fn) {
  var saida;
  try {
    saida = fn();
    saida.ok = true;
  } catch (err) {
    if (err instanceof ErroApi) {
      saida = { ok: false, codigo: err.codigo, mensagem: err.mensagem };
    } else {
      console.error(err);
      saida = { ok: false, codigo: 'ERRO', mensagem: 'Erro interno ao acessar a planilha.' };
    }
  }
  saida.versao = VERSAO_API;
  return ContentService.createTextOutput(JSON.stringify(saida)).setMimeType(ContentService.MimeType.JSON);
}

/**
 * Rode esta função uma vez pelo editor: ela pede as autorizações do Google,
 * prepara as colunas novas e mostra no registro o que foi encontrado.
 */
function testarConfiguracao() {
  if (!PropertiesService.getScriptProperties().getProperty('API_TOKEN')) {
    console.log('FALTA: propriedade API_TOKEN.');
    return;
  }
  var tabela = abrirTabela();
  var linhas = lerLinhas(tabela);
  var problemas = linhas.filter(function (l) { return l.status !== 'cancelada' && (!l.data || !l.inicio || !l.fim); });
  console.log('Aba: ' + tabela.aba.getName());
  console.log('Colunas: ' + tabela.cabecalho.join(' | '));
  console.log('Reservas lidas: ' + linhas.length + ' | com data ou hora ilegível: ' + problemas.length);
  problemas.slice(0, 10).forEach(function (l) { console.log('Verificar a linha ' + l.linha + ' da planilha.'); });
  console.log('OK');
}
