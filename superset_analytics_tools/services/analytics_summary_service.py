from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate


class AnalyticsSummaryService:
    def __init__(
        self,
        llm: BaseChatModel,
        max_summary_rows: int = 20,
    ):
        self.llm = llm
        self.max_summary_rows = max_summary_rows

    def _get_analytics_summary_prompt(self):
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
            You are an expert data analyst.

            You are given the output of a statistical analysis tool and the user's question.

            Your task is to answer the user's question using only the information contained
            in the analysis results.

            Guidelines:
            - Answer the user's question directly.
            - Explain the findings in clear, concise language.
            - Highlight important patterns, anomalies, trends, or relationships when they
            are supported by the analysis.
            - If no significant findings are present, clearly state that.
            - If the analysis cannot answer the user's question, explain why.
            - Do not speculate or infer causes that are not supported by the analysis.
            - Do not invent facts or statistics.
            - Base every conclusion only on the provided analysis results.
            - Keep the response concise (3–6 sentences).
            """,
                            ),
                            (
                                "human",
                                """
            User Question:
            {summary_question}

            Analysis Result:
            {analytics_result}
            """,
                            ),
                        ]
                    )

    def _get_raw_data_summary_prompt(self):
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                You are an expert data analyst.

                You are given a user's question and a small dataset.

                Your task is to answer the user's question using only the provided data.

                Guidelines:
                - Answer the user's question directly.
                - Summarize only what can be observed from the data.
                - Highlight any obvious patterns, relationships, or notable values if they are
                relevant to the user's question.
                - If the data is insufficient to answer the question, clearly state that.
                - Do not perform statistical analysis that requires more data than is available.
                - Do not speculate or invent facts.
                - Base every statement only on the provided data.
                - Keep the response concise (3–6 sentences).
                """,
                                ),
                                (
                                    "human",
                                    """
                User Question:
                {summary_question}

                Raw Data:
                {raw_data}
                """,
                                ),
                            ]
                        )

    def summarize_analytics(
        self,
        analytics_result: dict,
        summary_question: str,
    ) -> str:
        chain = self._get_analytics_summary_prompt() | self.llm

        response = chain.invoke(
            {
                "analytics_result": analytics_result,
                "summary_question": summary_question,
            }
        )

        return response.content

    def summarize_raw_data(
        self,
        raw_data: list[dict],
        summary_question: str,
    ) -> str:
        chain = self._get_raw_data_summary_prompt() | self.llm

        response = chain.invoke(
            {
                "raw_data": raw_data,
                "summary_question": summary_question,
            }
        )

        return response.content