import re
import sqlite3
import os

SAFE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")

BLOCKED = [
    "DROP ", "TRUNCATE ", "ALTER ", "CREATE USER",
    "GRANT ", "REVOKE ", "ATTACH ", "DETACH ",
    "PRAGMA KEY", "PRAGMA REKEY",
]


class RunSqlTool:
    name = "run_sql"
    description = (
        "Executa queries SQL em banco SQLite local. "
        "Input: {'db': 'banco.db', 'query': 'SELECT * FROM tabela'} "
        "Banco fica em workspace/. Suporta SELECT, INSERT, UPDATE, CREATE TABLE."
    )

    def run(self, input_data: dict) -> str:
        db_name = input_data.get("db", "")
        query   = input_data.get("query", "").strip()

        if not db_name:
            return "Erro: campo 'db' obrigatório. Ex: 'dados.db'"
        if not query:
            return "Erro: campo 'query' obrigatório."

        # normaliza toda sequência de espaço/tab/newline pra 1 espaço antes de checar —
        # sem isso "DROP\nTABLE x" bypassava o bloqueio (substring exige espaço literal).
        # Achado 2026-07-23, mesma classe de bug do git_tool corrigido mais cedo hoje.
        query_upper = re.sub(r"\s+", " ", query.upper())
        for keyword in BLOCKED:
            if keyword in query_upper:
                return f"Bloqueado: '{keyword.strip()}' não permitido por segurança."

        os.makedirs(SAFE_DIR, exist_ok=True)
        db_path = os.path.join(SAFE_DIR, os.path.basename(db_name))

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query)

            if query_upper.lstrip().startswith(("SELECT", "PRAGMA")):
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []

                if not rows:
                    return "Query retornou 0 resultados."

                header = " | ".join(cols)
                sep    = "-" * len(header)
                lines  = [header, sep]
                for row in rows[:50]:
                    lines.append(" | ".join(str(v) for v in row))

                suffix = f"\n... ({len(rows)} linhas total, mostrando 50)" if len(rows) > 50 else f"\n({len(rows)} linhas)"
                return "\n".join(lines) + suffix

            else:
                conn.commit()
                affected = cursor.rowcount
                return f"OK. Linhas afetadas: {affected}. Banco: {db_path}"

        except sqlite3.Error as e:
            return f"Erro SQL: {str(e)}"
        except Exception as e:
            return f"Erro: {str(e)}"
        finally:
            conn.close()
