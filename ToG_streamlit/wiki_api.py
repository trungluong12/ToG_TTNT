"""Util that calls Wikidata."""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from pydantic import BaseModel, model_validator
"""Tool for the Wikidata API."""
from wikibase_rest_api_client.utilities.fluent import FluentWikibaseClient
from typing import Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool

from langchain_community.utilities.wikidata import WikidataAPIWrapper

logger = logging.getLogger(__name__)

WIKIDATA_MAX_QUERY_LENGTH = 300
# Common properties you probably want to see filtered from https://www.wikidata.org/wiki/Wikidata:Database_reports/List_of_properties/all
DEFAULT_PROPERTIES = [
    "P31",
    "P279",
    "P27",
    "P361",
    "P527",
    "P495",
    "P17",
    "P585",
    "P131",
    "P106",
    "P21",
    "P569",
    "P570",
    "P577",
    "P50",
    "P571",
    "P641",
    "P625",
    "P19",
    "P69",
    "P108",
    "P136",
    "P39",
    "P161",
    "P20",
    "P101",
    "P179",
    "P175",
    "P7937",
    "P57",
    "P607",
    "P509",
    "P800",
    "P449",
    "P580",
    "P582",
    "P276",
    "P69",
    "P112",
    "P740",
    "P159",
    "P452",
    "P102",
    "P1142",
    "P1387",
    "P1576",
    "P140",
    "P178",
    "P287",
    "P25",
    "P22",
    "P40",
    "P185",
    "P802",
    "P1416",
]
DEFAULT_LANG_CODE = "en"
WIKIDATA_USER_AGENT = "langchain-wikidata"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_REST_API_URL = "https://www.wikidata.org/w/rest.php/wikibase/v1/"


class WikidataAPIWrapper(BaseModel):
    """Wrapper around the Wikidata API.

    To use, you should have the ``wikibase-rest-api-client`` and
    ``mediawikiapi `` python packages installed.
    This wrapper will use the Wikibase APIs to conduct searches and
    fetch item content. By default, it will return the item content
    of the top-k results.
    It limits the Document content by doc_content_chars_max.
    """

    wikidata_mw: Any  #: :meta private:
    wikidata_rest: Any  # : :meta private:
    top_k_results: int = 2
    load_all_available_meta: bool = False
    doc_content_chars_max: int = 4000
    wikidata_props: List[str] = DEFAULT_PROPERTIES
    lang: str = DEFAULT_LANG_CODE

    @model_validator(mode="before")
    @classmethod
    def validate_environment(cls, values: Dict) -> Any:
        """Validate that the python package exists in environment."""
        try:
            from mediawikiapi import MediaWikiAPI
            from mediawikiapi.config import Config

            values["wikidata_mw"] = MediaWikiAPI(
                Config(user_agent=WIKIDATA_USER_AGENT, mediawiki_url=WIKIDATA_API_URL)
            )
        except ImportError:
            raise ImportError(
                "Could not import mediawikiapi python package. "
                "Please install it with `pip install mediawikiapi`."
            )

        try:
            from wikibase_rest_api_client import Client

            client = Client(
                timeout=60,
                base_url=WIKIDATA_REST_API_URL,
                headers={"User-Agent": WIKIDATA_USER_AGENT},
                follow_redirects=True,
            )
            values["wikidata_rest"] = client
        except ImportError:
            raise ImportError(
                "Could not import wikibase_rest_api_client python package. "
                "Please install it with `pip install wikibase-rest-api-client`."
            )
        return values

    def _item_to_document(self, qid: str) -> Optional[Document]:
        fluent_client: FluentWikibaseClient = FluentWikibaseClient(
            self.wikidata_rest, supported_props=self.wikidata_props, lang=self.lang
        )
        resp = fluent_client.get_item(qid)

        if not resp:
            logger.warning(f"Could not find item {qid} in Wikidata")
            return None

        doc_lines = []
        if resp.label:
            doc_lines.append(f"Label: {resp.label}")
        if resp.description:
            doc_lines.append(f"Description: {resp.description}")
        if resp.aliases:
            doc_lines.append(f"Aliases: {', '.join(resp.aliases)}")
        for prop, values in resp.statements.items():
            if values:
                doc_lines.append(
                    f"{prop.label}: {', '.join([v.value or 'unknown' for v in values])}"
                )

        return Document(
            page_content=("\n".join(doc_lines))[: self.doc_content_chars_max],
            meta={"title": qid, "source": f"https://www.wikidata.org/wiki/{qid}"},
        )

    def load(self, query: str) -> List[Document]:
        """
        Run Wikidata search and get the item documents plus the meta information.
        """

        clipped_query = query[:WIKIDATA_MAX_QUERY_LENGTH]
        items = self.wikidata_mw.search(clipped_query, results=self.top_k_results)
        docs = []
        for item in items[: self.top_k_results]:
            if doc := self._item_to_document(item):
                docs.append(doc)
        return docs

    def run(self, query: str) -> str:
        """Run Wikidata search and get item summaries."""

        clipped_query = query[:WIKIDATA_MAX_QUERY_LENGTH]
        items = self.wikidata_mw.search(clipped_query, results=self.top_k_results)

        docs = []
        for item in items[: self.top_k_results]:
            if doc := self._item_to_document(item):
                docs.append(f"Result {item}:\n{doc.page_content}")
        if not docs:
            return "No good Wikidata Search Result was found"
        return "\n\n".join(docs)[: self.doc_content_chars_max]

    def run_item_id(self, qid):
        """Run Wikidata search and get item summaries."""
        fluent_client = FluentWikibaseClient(
            self.wikidata_rest, supported_props=self.wikidata_props, lang=self.lang
        )
        resp = fluent_client.get_item(qid)
        
        relations = []
        entity_names = {}
        entity_ids = {}
        id_to_label = {}
        label_to_id = {}

        for prop, values in resp.statements.items():
            if values:
                entity_values = [v.value or 'unknown' for v in values]
                entity_qids = [v.qid or 'unknown' for v in values]

                # Check if all values are 'unknown'
                if all(val == 'unknown' for val in entity_values):
                    continue  # Skip adding this property if all values are unknown

                relations.append(f"wiki.relation.{prop.label}")
                entity_names[prop.label] = entity_values
                entity_ids[prop.label] = entity_qids

                for v in values:
                    if v.qid and v.value:
                        id_to_label[v.qid] = v.value
                        label_to_id[v.value] = v.qid

        return relations, entity_names, entity_ids, id_to_label, label_to_id

    

class WikidataQueryRun(BaseTool):  # type: ignore[override]
    """Tool that searches the Wikidata API."""

    name: str = "Wikidata"
    description: str = (
        "A wrapper around Wikidata. "
        "Useful for when you need to answer general questions about "
        "people, places, companies, facts, historical events, or other subjects. "
        "Input should be the exact name of the item you want information about "
        "or a Wikidata QID."
    )
    api_wrapper: WikidataAPIWrapper

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the Wikidata tool."""
        return self.api_wrapper.run(query)
    

# wikidata = WikidataQueryRun(api_wrapper=WikidataAPIWrapper())
wikidata = WikidataAPIWrapper()

