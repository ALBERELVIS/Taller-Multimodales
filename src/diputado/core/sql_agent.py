"""Agente de lenguaje natural a SQL para el analista (smolagents + Qwen2.5 en Ollama).

Seguimos el patrón del notebook 9 de referencia (CodeAgent con una herramienta SQL),
pero con un LLM local y con la base abierta en modo de solo lectura. Si el agente
falla (los modelos de 7B a veces se pierden), caemos a una traducción directa
pregunta -> SQL en una única llamada, que es más predecible.
"""

from __future__ import annotations

import time

import pandas as pd

from diputado import config
from diputado.ai import ollama_client
from diputado.ai.gpu import gpu
from diputado.core import cases_db

FEW_SHOT = """Ejemplos:
P: ¿Cuántos casos rojos hubo la última semana?
SQL: SELECT COUNT(*) AS casos_rojos FROM casos WHERE nivel='rojo' AND fecha >= datetime('now','-7 day')
P: ¿Qué campañas son las más frecuentes este mes?
SQL: SELECT campana, COUNT(*) AS n FROM casos WHERE campana IS NOT NULL AND fecha >= datetime('now','-30 day') GROUP BY campana ORDER BY n DESC LIMIT 10
P: ¿Cuánto dinero se intentó robar con el falso familiar?
SQL: SELECT ROUND(SUM(importe_eur),2) AS total_eur, COUNT(*) AS casos FROM casos WHERE tacticas LIKE '%falso_familiar%'"""


class SQLAgent:
    def __init__(self) -> None:
        self.last_sql: str | None = None
        self.last_df: pd.DataFrame | None = None
        self._agent = None

    def _tool(self):
        from smolagents import tool

        agent_self = self

        @tool
        def consultar_casos(sql: str) -> str:
            """Ejecuta una consulta SQL SELECT de solo lectura sobre la base de casos de fraude (SQLite).

            Args:
                sql: Una única consulta SELECT válida en SQLite.
            """
            try:
                df = cases_db.safe_query(sql)
            except Exception as exc:
                return f"Error: {exc}"
            agent_self.last_sql, agent_self.last_df = sql, df
            return df.to_string(index=False, max_rows=30) if len(df) else "La consulta no ha devuelto filas."

        consultar_casos.description += "\n\n" + cases_db.SCHEMA_DOC
        return consultar_casos

    def _get_agent(self):
        if self._agent is None:
            from smolagents import CodeAgent, LiteLLMModel

            model = LiteLLMModel(
                model_id=f"ollama_chat/{config.OLLAMA_AGENT_LLM}",
                api_base=config.OLLAMA_HOST,
                num_ctx=8192,
                temperature=0.0,
            )
            self._agent = CodeAgent(tools=[self._tool()], model=model, max_steps=4, verbosity_level=0)
        return self._agent

    def _direct(self, question: str) -> tuple[str, str]:
        schema = {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}
        prompt = f"{cases_db.SCHEMA_DOC}\n\n{FEW_SHOT}\n\nTraduce a UNA consulta SQLite de lectura.\nP: {question}"
        data, _ = ollama_client.chat(config.OLLAMA_AGENT_LLM, [{"role": "user", "content": prompt}], schema=schema)
        sql = data["sql"]
        df = cases_db.safe_query(sql)
        self.last_sql, self.last_df = sql, df
        if len(df) == 1 and df.shape[1] <= 3:
            summary = ", ".join(f"{c}: {v}" for c, v in df.iloc[0].items())
            return f"Resultado: {summary}.", "consulta directa"
        return f"He encontrado {len(df)} filas; las muestro en la tabla.", "consulta directa"

    def ask(self, question: str, use_agent: bool = True) -> dict:
        self.last_sql, self.last_df = None, None
        t0 = time.perf_counter()
        answer, mode = None, None
        if use_agent:
            try:
                with gpu.claim("ollama"):
                    result = self._get_agent().run(
                        f"{question}\nUsa la herramienta consultar_casos. Responde en español con una frase final concreta."
                    )
                answer, mode = str(result), "agente smolagents (CodeAgent)"
            except Exception:
                answer = None
        if answer is None or self.last_sql is None:
            try:
                answer, mode = self._direct(question)
            except Exception as exc:
                answer, mode = f"No he podido responder a esa pregunta ({exc}).", "error"
        return {
            "answer": answer,
            "sql": self.last_sql,
            "df": self.last_df if self.last_df is not None else pd.DataFrame(),
            "mode": mode,
            "ms": (time.perf_counter() - t0) * 1000,
        }


agent = SQLAgent()
