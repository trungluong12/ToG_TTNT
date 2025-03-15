import argparse
import random
import streamlit as st
import openai

from client import MultiServerWikidataQueryClient
from freebase_func import entity_prune, entity_score, half_stop, reasoning, update_history
from utils import generate_without_explored_paths, if_finish_list, save_2_jsonl
from wiki_func import del_all_unknown_entity
from wiki_spasql import relation_search_prune_API_ver2

# Cấu hình API Key của OpenAI
openai.api_key = "YOUR_OPENAI_API_KEY"

def get_response(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

# Giao diện Streamlit
st.title("Simple Chatbot with Streamlit")

# Lịch sử hội thoại
if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị tin nhắn trước đó
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

parser = argparse.ArgumentParser()
parser.add_argument("--dataset", type=str, default="webqsp", help="Choose the dataset.")
parser.add_argument("--max_length", type=int, default=256, help="Max length of LLM output.")
parser.add_argument("--temperature_exploration", type=float, default=0.4, help="Temperature in exploration stage.")
parser.add_argument("--temperature_reasoning", type=float, default=0, help="Temperature in reasoning stage.")
parser.add_argument("--width", type=int, default=3, help="Search width of ToG.")
parser.add_argument("--depth", type=int, default=3, help="Search depth of ToG.")
parser.add_argument("--remove_unnecessary_rel", type=bool, default=True, help="Remove unnecessary relations.")
parser.add_argument("--LLM_type", type=str, default="gpt-3.5-turbo", help="Base LLM model.")
parser.add_argument("--opeani_api_keys", type=str, default="", help="OpenAI API keys.")
parser.add_argument("--num_retain_entity", type=int, default=5, help="Number of retained entities.")
parser.add_argument("--prune_tools", type=str, default="llm", help="Prune tools for ToG.")

# Parse arguments
args = parser.parse_args([
    "--dataset", "cwq",
    "--max_length", "256",
    "--temperature_exploration", "0.4",
    "--temperature_reasoning", "0",
    "--width", "3",
    "--depth", "3",
    "--remove_unnecessary_rel", "True",
    "--LLM_type", "gpt-3.5-turbo",
    "--opeani_api_keys", "AIzaSyDWJo9zAS4riInDnb5KX6xq6DgO5fhEkvA",
    "--num_retain_entity", "5",
    "--prune_tools", "bm25"
])

# Nhập câu hỏi từ người dùng
prompt = st.chat_input("Type your message...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Lấy phản hồi từ chatbot
    response = prompt
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)
        question = "What building in Vienna, Austria has 50 floors"
        topic_entity = {
            "Q1741": "Vienna"
        }
        cluster_chain_of_entities = []
        if len(topic_entity) == 0:
            results = generate_without_explored_paths(question, args)
            save_2_jsonl(question, results, [], file_name=args.dataset)
            # continue
        pre_relations = []
        pre_heads= [-1] * len(topic_entity)
        flag_printed = False
        st.markdown(len(topic_entity))
        # with open(args.addr_list, "r") as f:
        #     server_addrs = f.readlines()
        #     server_addrs = [addr.strip() for addr in server_addrs]
        # # print(f"Server addresses: {server_addrs}")
        # wiki_client = MultiServerWikidataQueryClient(server_addrs)
        wiki_id_to_label = {}
        wiki_id_to_label.update(topic_entity)
        wiki_label_to_id = {}
        for depth in range(1, args.depth+1):
            current_entity_relations_list = []
            current_entity_names = {} 
            current_entity_ids = {}
            i=0
            for entity in topic_entity:
                if entity!="[FINISH_ID]":
                    retrieve_relations_with_scores, entity_names, entity_ids, id_to_label, label_to_id = relation_search_prune_API_ver2(entity, topic_entity[entity], pre_relations, pre_heads[i], question, args, "dummy str")  # best entity triplet, entitiy_id
                    st.markdown(retrieve_relations_with_scores)
        #             current_entity_ids[entity] = entity_ids 
        #             current_entity_names[entity] = entity_names 
        #             wiki_id_to_label.update(id_to_label) 
        #             wiki_label_to_id.update(label_to_id)
        #             current_entity_relations_list.extend(retrieve_relations_with_scores)
                    
        #         i+=1
        #     total_candidates = []
        #     total_scores = []
        #     total_relations = []
        #     total_entities_id = []
        #     total_topic_entities = []
        #     total_head = []

        #     for entity in current_entity_relations_list:
        #         value_flag=False
        #         # if entity['head']:
        #         #     entity_candidates_id, entity_candidates_name = entity_search(entity['entity'], entity['relation'], wiki_client, True)
        #         # else:
        #         #     entity_candidates_id, entity_candidates_name = entity_search(entity['entity'], entity['relation'], wiki_client, False)
        #         # có thể có bug chỗ này 
        #         if entity['relation'] not in current_entity_ids[entity['entity']] or entity['relation'] not in current_entity_names[entity['entity']]: 
        #             continue 
        #         entity_candidates_id = current_entity_ids[entity['entity']][entity['relation']]
        #         entity_candidates_name = current_entity_names[entity['entity']][entity['relation']]
        #         if len(entity_candidates_name)==0:
        #             continue
        #         if len(entity_candidates_id) ==0: # values
        #             value_flag=True
        #             if len(entity_candidates_name) >=20:
        #                 entity_candidates_name = random.sample(entity_candidates_name, 10)
        #             entity_candidates_id = ["[FINISH_ID]"] * len(entity_candidates_name)
        #         else: # ids
        #             entity_candidates_id, entity_candidates_name = del_all_unknown_entity(entity_candidates_id, entity_candidates_name)
        #             if len(entity_candidates_id) >=20:
        #                 indices = random.sample(range(len(entity_candidates_name)), 10)
        #                 entity_candidates_id = [entity_candidates_id[i] for i in indices]
        #                 entity_candidates_name = [entity_candidates_name[i] for i in indices]

        #         if len(entity_candidates_id) ==0:
        #             continue

        #         scores, entity_candidates, entity_candidates_id = entity_score(question, entity_candidates_id, entity_candidates_name, entity['score'], entity['relation'], args)
                
        #         total_candidates, total_scores, total_relations, total_entities_id, total_topic_entities, total_head = update_history(entity_candidates, entity, scores, entity_candidates_id, total_candidates, total_scores, total_relations, total_entities_id, total_topic_entities, total_head, value_flag)
            
        #     if len(total_candidates) ==0:
        #         half_stop(question, cluster_chain_of_entities, depth, args)
        #         flag_printed = True
        #         break
                
        #     flag, chain_of_entities, entities_id, pre_relations, pre_heads = entity_prune(total_entities_id, total_relations, total_candidates, total_topic_entities, total_head, total_scores, args, wiki_client, wiki_id_to_label)
        #     cluster_chain_of_entities.append(chain_of_entities)
        #     if flag:
        #         stop, results = reasoning(question, cluster_chain_of_entities, args)
        #         if stop:
        #             print("ToG stoped at depth %d." % depth)
        #             save_2_jsonl(question, results, cluster_chain_of_entities, file_name=args.dataset)
        #             flag_printed = True
        #             break
        #         else:
        #             print("depth %d still not find the answer." % depth)
        #             flag_finish, entities_id = if_finish_list(entities_id)
        #             if flag_finish:
        #                 half_stop(question, cluster_chain_of_entities, depth, args)
        #                 flag_printed = True
        #             else:
        #                 topic_entity = {qid: topic for qid, topic in zip(entities_id, [wiki_id_to_label[entity] for entity in entities_id])}
        #                 continue
        #     else:
        #         half_stop(question, cluster_chain_of_entities, depth, args)
        #         flag_printed = True
        
        # if not flag_printed:
        #     results = generate_without_explored_paths(question, args)
        #     save_2_jsonl(question, results, [], file_name=args.dataset)

