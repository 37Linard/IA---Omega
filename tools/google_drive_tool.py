import os
import json
import logging

log = logging.getLogger(__name__)

CREDS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gdrive_credentials.json")
TOKEN_FILE  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gdrive_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def _get_creds():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        raise RuntimeError(
            "Dependências ausentes. Execute: "
            "pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                raise RuntimeError(
                    "Arquivo gdrive_credentials.json não encontrado na pasta do projeto.\n"
                    "Para configurar:\n"
                    "1. Acesse console.cloud.google.com\n"
                    "2. Crie um projeto → ative Google Drive API e Google Docs API\n"
                    "3. Credenciais → Criar → OAuth 2.0 → App de computador\n"
                    "4. Baixe o JSON e salve como gdrive_credentials.json na pasta C:\\Users\\User\\Desktop\\MEU\\IA\\"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def _drive():
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=_get_creds())


def _docs():
    from googleapiclient.discovery import build
    return build("docs", "v1", credentials=_get_creds())


def _list_files(query: str = "", limit: int = 20) -> str:
    svc = _drive()
    q_parts = ["mimeType='application/vnd.google-apps.document'", "trashed=false"]
    if query:
        q_parts.append(f"name contains '{query}'")
    results = svc.files().list(
        q=" and ".join(q_parts),
        pageSize=min(limit, 50),
        fields="files(id,name,modifiedTime)",
        orderBy="modifiedTime desc",
    ).execute()
    files = results.get("files", [])
    if not files:
        return "Nenhum documento encontrado no Google Drive."
    lines = [f"Documentos no Google Drive ({len(files)}):"]
    for f in files:
        modified = f.get("modifiedTime", "")[:10]
        lines.append(f"  [{f['id']}] {f['name']} — modificado: {modified}")
    return "\n".join(lines)


def _read_doc(file_id: str) -> str:
    svc = _drive()
    content = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
    text = content.decode("utf-8") if isinstance(content, bytes) else content
    if not text.strip():
        return "Documento vazio."
    return text[:5000] + ("\n\n[Conteúdo truncado — documento tem mais texto]" if len(text) > 5000 else "")


def _create_doc(title: str, content: str) -> str:
    docs_svc = _docs()
    doc = docs_svc.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    if content:
        requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
        docs_svc.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return f"Documento criado: {title}\nID: {doc_id}\nURL: {url}"


def _update_doc(file_id: str, content: str, mode: str = "append") -> str:
    docs_svc = _docs()
    doc = docs_svc.documents().get(documentId=file_id).execute()
    body_content = doc.get("body", {}).get("content", [])

    if mode == "append":
        # Insert at end (before final newline)
        end_index = body_content[-1]["endIndex"] - 1 if body_content else 1
        end_index = max(end_index, 1)
        requests = [{"insertText": {"location": {"index": end_index}, "text": f"\n{content}"}}]
    else:
        # Replace: delete all then insert
        total_end = body_content[-1]["endIndex"] - 1 if body_content else 1
        requests = []
        if total_end > 1:
            requests.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": total_end}}})
        requests.append({"insertText": {"location": {"index": 1}, "text": content}})

    docs_svc.documents().batchUpdate(documentId=file_id, body={"requests": requests}).execute()
    title = doc.get("title", file_id)
    return f"Documento '{title}' atualizado com sucesso (modo: {mode})."


class GoogleDriveTool:
    name = "google_drive"
    description = (
        "Acessa Google Drive para ler, criar e atualizar Google Docs. "
        "Ações: 'list' (listar docs), 'read' (ler conteúdo), 'create' (criar doc), 'update' (editar doc). "
        "Input: {'action': 'list', 'query': 'relatorio'} | "
        "{'action': 'read', 'file_id': 'ID_DO_DOC'} | "
        "{'action': 'create', 'title': 'Meu Doc', 'content': 'Texto...'} | "
        "{'action': 'update', 'file_id': 'ID', 'content': 'Novo texto', 'mode': 'append'}"
    )

    def run(self, params: dict) -> str:
        action = params.get("action", "").strip().lower()

        try:
            if action == "list":
                return _list_files(
                    query=params.get("query", ""),
                    limit=int(params.get("limit", 20)),
                )
            elif action == "read":
                file_id = params.get("file_id", "").strip()
                if not file_id:
                    return "Erro: forneça 'file_id' do documento."
                return _read_doc(file_id)
            elif action == "create":
                title   = params.get("title", "Novo Documento").strip()
                content = params.get("content", "")
                return _create_doc(title, content)
            elif action == "update":
                file_id = params.get("file_id", "").strip()
                content = params.get("content", "")
                mode    = params.get("mode", "append")
                if not file_id:
                    return "Erro: forneça 'file_id' do documento."
                if mode not in ("append", "replace"):
                    mode = "append"
                return _update_doc(file_id, content, mode)
            else:
                return (
                    "Ação inválida. Use: 'list', 'read', 'create' ou 'update'.\n"
                    "Exemplo: {\"action\": \"list\", \"query\": \"relatorio\"}"
                )
        except RuntimeError as e:
            return f"Erro: {e}"
        except Exception as e:
            log.exception("GoogleDriveTool erro")
            return f"Erro no Google Drive: {e}"
