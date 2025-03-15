from utils import run_llm
from wiki_func import abandon_rels, clean_relations, construct_relation_prune_prompt
from qwikidata.sparql import return_sparql_query_results

def get_wikidata_relations(entity_id):
    """
    Truy vấn Wikidata để lấy các quan hệ (head & tail) của thực thể `entity_id`.

    Args:
        entity_id (str): ID của thực thể trên Wikidata (ví dụ: "Q3077690").

    Returns:
        tuple[list[dict], dict, dict]: 
            - `relations` (list[dict]): Danh sách từ điển chứa 5 giá trị:
                - type_entity (str): "HEAD" hoặc "TAIL"
                - property_id (str): ID thuộc tính (Pxxx)
                - property_label (str): Nhãn thuộc tính
                - value_id (str): ID thực thể (Qxxx)
                - value_label (str): Nhãn thực thể
            - `id_to_label` (dict): Mapping từ ID thực thể (`Qxxx`) sang nhãn (`value_label`)
            - `label_to_id` (dict): Mapping từ nhãn (`value_label`) sang ID thực thể (`Qxxx`)
    """

    query_string = f"""
    SELECT ?property ?propertyLabel ?value ?valueLabel ?type_entity WHERE {{
      {{
        SELECT ?property ?value ?type_entity WHERE {{
          wd:{entity_id} ?p ?value.
          ?property wikibase:directClaim ?p.
          BIND("head" AS ?type_entity)
        }} LIMIT 100
      }}
      UNION
      {{
        SELECT ?property ?value ?type_entity WHERE {{
          ?value ?p wd:{entity_id}.
          ?property wikibase:directClaim ?p.
          BIND("tail" AS ?type_entity)
        }} LIMIT 100
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """

    # Gửi truy vấn SPARQL
    res = return_sparql_query_results(query_string)

    # Khởi tạo danh sách và từ điển
    relations = []
    id_to_label = {}
    label_to_id = {}

    # Xử lý kết quả
    for result in res["results"]["bindings"]:
        property_id = result["property"]["value"].split("/")[-1]  # Lấy ID thuộc tính (Pxxx)
        property_label = result["propertyLabel"]["value"]  # Nhãn thuộc tính
        value_id = result["value"]["value"].split("/")[-1]  # Lấy ID thực thể (Qxxx hoặc giá trị khác)

        # Chỉ lấy thực thể có ID bắt đầu bằng "Q"
        if value_id.startswith("Q"):
            value_label = result["valueLabel"]["value"] if "valueLabel" in result else value_id  # Nhãn thực thể
            type_entity = result["type_entity"]["value"].upper()  # HEAD hoặc TAIL
            
            # Lưu vào danh sách relations
            relations.append({
                "type_entity": type_entity,
                "property_id": property_id,
                "property_label": property_label,
                "value_id": value_id,
                "value_label": value_label
            })

            # Cập nhật id_to_label và label_to_id
            id_to_label[value_id] = value_label
            label_to_id[value_label] = value_id

    return relations, id_to_label, label_to_id


def get_entity_and_relation(entity_id): 
    relations, id_to_label, label_to_id = get_wikidata_relations(entity_id)
    relations_process = {'head': [], 'tail': []}
    entity_names = {}
    entity_ids = {}

    for relation in relations:
        type_entity = relation['type_entity'].lower()
        property_label = relation['property_label']
        property_label = f"{property_label}"
        value_label = relation['value_label']
        value_id = relation['value_id']

        # Append formatted relation string
        if property_label not in relations_process[type_entity]:
            relations_process[type_entity].append(property_label)

        # Update entity_names and entity_ids
        if property_label not in entity_names:
            entity_names[property_label] = []
        if property_label not in entity_ids:
            entity_ids[property_label] = []

        entity_names[property_label].append(value_label)
        entity_ids[property_label].append(value_id)

    return relations_process, id_to_label, label_to_id, entity_names, entity_ids

def relation_search_prune_API_ver2(entity_id, entity_name, pre_relations, pre_head, question, args, wiki_client):
    relations, id_to_label, label_to_id, entity_names, entity_ids = get_entity_and_relation(entity_id)
    head_relations = [rel for rel in relations['head']]
    tail_relations = [rel for rel in relations['tail']]
    if args.remove_unnecessary_rel:
        head_relations = [relation for relation in head_relations if not abandon_rels(relation)]
        tail_relations = [relation for relation in tail_relations if not abandon_rels(relation)]
    if pre_head:
        tail_relations = list(set(tail_relations) - set(pre_relations))
    else:
        head_relations = list(set(head_relations) - set(pre_relations))

    head_relations = list(set(head_relations))
    tail_relations = list(set(tail_relations))
    total_relations = head_relations+tail_relations
    total_relations.sort()  # make sure the order in prompt is always equal
    
    prompt = construct_relation_prune_prompt(question, entity_name, total_relations, args)

    result = run_llm(prompt, args.temperature_exploration, args.max_length, args.opeani_api_keys, args.LLM_type)
    flag, retrieve_relations_with_scores = clean_relations(result, entity_id, head_relations) 

    if flag:
        for retrive_relation in retrieve_relations_with_scores:
            if retrive_relation['relation'] not in entity_ids:
                print(f"Relation {retrive_relation['relation']} not in current_entity_ids[{entity_id}]: {entity_ids.keys()}")
        return retrieve_relations_with_scores, entity_names, entity_ids, id_to_label, label_to_id
    else:
        return [], {}, {}, {}, {} # format error or too small max_length

# Ví dụ: lấy dữ liệu cho entity Q3077690
entity_id = "Q3077690"
relations, id_to_label, label_to_id = get_wikidata_relations(entity_id)

# In kết quả relations
print("Type | Property ID | Property Label | Value ID | Value Label")
print("-" * 80)
for r in relations:
    print(f"{r['type_entity']} | {r['property_id']} | {r['property_label']} | {r['value_id']} | {r['value_label']}")

# In mapping ID → Label
print("\nID to Label Mapping:")
for qid, label in id_to_label.items():
    print(f"{qid} → {label}")

# In mapping Label → ID
print("\nLabel to ID Mapping:")
for label, qid in label_to_id.items():
    print(f"{label} → {qid}")
