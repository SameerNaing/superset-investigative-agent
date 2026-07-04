from dotenv import load_dotenv
from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage

from prompt import SYSTEM_PROMPT
from superset_analytics_tools.tools import superset_tools, analytics_tools

load_dotenv()

tools = [
    # superset tools
    superset_tools.get_chart_list,
    superset_tools.get_chart_detail,
    superset_tools.generate_evidence_chart,
    superset_tools.get_dataset_list,
    superset_tools.get_dataset_detail,
    superset_tools.execute_sql,

    # analytics tools — summarize_chart_data removed.
    # Small datasets are auto-summarized inside get_chart_detail.
    # Anomaly results include a plain-language 'interpretation' field automatically.
    analytics_tools.detect_timeseries_anomalies,
    analytics_tools.detect_cross_section_anomalies,
    analytics_tools.detect_relationship_anomalies,
]

_glossary_path = Path(__file__).parent / "mining-glossary.yml"
_glossary_text = _glossary_path.read_text(encoding="utf-8")


model = init_chat_model("gpt-5.4")
FULL_PROMPT = (
    SYSTEM_PROMPT
    + "\n\n"
    + "━" * 47 + "\n"
    + "DOMAIN GLOSSARY\n"
    + "━" * 47 + "\n"
    + "The following glossary defines domain-specific terms, metrics, rules, and\n"
    + "relationships present in this dataset. Use it to interpret column values,\n"
    + "choose the right filters, and explain findings in domain language.\n\n"
    + _glossary_text
)


agent = create_agent(
    model=model,
    tools=tools,
    system_prompt=SystemMessage(content=FULL_PROMPT),
)



