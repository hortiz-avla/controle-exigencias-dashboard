# Dashboard de Controle de Exigências

Aplicativo Streamlit para acompanhar a guia `Base` do Google Sheets.

## Recursos

- indicadores de total, andamento, atraso e conclusão;
- atraso médio;
- filtros por status, segurado, inspetor, texto e prazo;
- ranking de segurados com pendências;
- alerta de vencimentos nos próximos 15 dias;
- tabela detalhada com descrição e link do arquivo;
- download dos dados filtrados;
- atualização dos dados a cada 60 segundos;
- modo demonstração quando não existem credenciais configuradas.

## Executar localmente

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Conectar ao Google Sheets com segurança

1. No Google Cloud, crie ou selecione um projeto.
2. Ative as APIs **Google Sheets API** e **Google Drive API**.
3. Crie uma conta de serviço e baixe a chave JSON.
4. Compartilhe a planilha com o `client_email` da conta de serviço como leitor.
5. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
6. Informe o ID da planilha e os campos da chave JSON.
7. Nunca envie `secrets.toml` ao GitHub.

O ID da planilha é o trecho entre `/d/` e `/edit` na URL do Google Sheets.

## Publicação

Envie o projeto para um repositório GitHub, crie um aplicativo no Streamlit
Community Cloud apontando para `dashboard/app.py` e cole o conteúdo de
`secrets.toml` na área **Secrets** da aplicação.

Se os dados contiverem e-mails, endereços ou informações internas, restrinja o
acesso ao aplicativo em vez de torná-lo público.
