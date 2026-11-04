# SEMED | Agendamento da Sala de Reuniões

App para reservar a sala pelo celular ou computador. Os dados ficam na planilha Google; o Apps Script controla as regras (conflitos, cancelamentos) e o app Streamlit é a interface.

| Arquivo | O que é |
|---|---|
| `app.py` | Telas do sistema |
| `nucleo.py` | Regras de horário e comunicação com o Apps Script |
| `apps_script/Code.gs` | Código a colar no Apps Script da planilha |
| `.streamlit/secrets.toml` | URL e senhas. **Nunca compartilhe nem envie ao GitHub** |
| `testes/` | Testes automáticos |
| `_versao_anterior/` | Cópia do app antigo |

## Colocar no ar

### 1. Atualizar o Apps Script
1. Faça uma cópia de segurança da planilha: **Arquivo > Fazer uma cópia**.
2. Abra o projeto do Apps Script atual. Guarde o código antigo em um arquivo de texto e substitua-o por todo o conteúdo de `apps_script/Code.gs`.
3. Em **Configurações do projeto > Propriedades do script**, adicione:
   - `API_TOKEN`: o mesmo valor de `API_TOKEN` em `.streamlit/secrets.toml`.
   - `SPREADSHEET_ID`: somente se o script não tiver sido aberto pela planilha (**Extensões > Apps Script**). É o trecho da URL da planilha entre `/d/` e `/edit`.
   - `SHEET_NAME`: somente se as reservas não estiverem na primeira aba.
4. No editor, selecione a função `testarConfiguracao` e clique em **Executar**. Autorize o acesso e confira no registro a aba, as colunas e o total de reservas lidas. A função acrescenta colunas novas no fim da planilha; as existentes não mudam.
5. Vá em **Implantar > Gerenciar implantações**, clique no lápis e escolha **Versão: Nova versão**. Mantenha "Executar como: eu" e "Quem pode acessar: qualquer pessoa". A URL continua a mesma.

Se `testarConfiguracao` informar "Coluna(s) não encontrada(s)", ajuste o título dessa coluna na planilha (por exemplo, para `Responsavel`) e rode de novo.

### 2. Testar no computador
Na pasta do projeto:
```
venv\Scripts\python -m streamlit run app.py
```

### 3. Publicar (Streamlit Community Cloud, gratuito)
1. Envie o projeto a um repositório no GitHub. O `.gitignore` já deixa de fora as senhas e a versão antiga.
2. Em [share.streamlit.io](https://share.streamlit.io), crie o app apontando para `app.py`. Em **Advanced settings**, escolha Python 3.11 ou mais recente.
3. Em **Settings > Secrets**, cole as quatro primeiras linhas de `.streamlit/secrets.toml`.
4. Envie o link e a senha de acesso à equipe. No celular, use **Adicionar à tela inicial** para abrir como um aplicativo.

## Uso no dia a dia
- **Senha de acesso:** a equipe usa para entrar. Para trocar, altere `SENHA_ACESSO` nos secrets.
- **Senha de administrador:** em **Mais**, libera o cancelamento sem código e a exportação em CSV.
- **Código de cancelamento:** aparece uma única vez ao reservar. Quem perder o código pede o cancelamento ao administrador. Reservas antigas não têm código: só o administrador as cancela.
- **Cancelamentos:** a linha continua na planilha com `Status = Cancelada`, mantendo o histórico.
- **Edição direta na planilha:** é permitida, desde que os títulos das colunas não mudem. Se mudarem, o sistema mostra um erro em vez de ignorar reservas.
- **Horário de funcionamento:** 07:00 às 20:00. Para mudar, altere `HORA_ABERTURA` e `HORA_FECHAMENTO` em `nucleo.py` e em `Code.gs` (depois, publique uma nova versão do script).

## Se algo der errado
| Mensagem | O que fazer |
|---|---|
| "O Apps Script publicado é a versão antiga" | Refaça o passo 1.5 |
| "Acesso não autorizado" | `API_TOKEN` diferente entre o script e os secrets |
| "A planilha respondeu de forma inesperada" | Confira "Quem pode acessar: qualquer pessoa" na implantação |
| "Coluna(s) não encontrada(s)" | Um título de coluna foi alterado na planilha |

## Testes
```
venv\Scripts\python -m unittest discover testes
```
