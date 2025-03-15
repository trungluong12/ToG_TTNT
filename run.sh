cd /mnt/d/KHDL/Paper/RAG/ToG_TTNT/ToG

python /mnt/d/KHDL/Paper/RAG/ToG_TTNT/ToG/main_wiki.py \
    --dataset cwq \
    --max_length 256 \
    --temperature_exploration 0.4 \
    --temperature_reasoning 0 \
    --width 3 \
    --depth 3 \
    --remove_unnecessary_rel True \
    --LLM_type gpt-3.5-turbo \
    --opeani_api_keys $LLM_API\
    --num_retain_entity 5 \
    --prune_tools llm