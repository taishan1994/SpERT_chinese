import json
import re
from pprint import pprint

from tqdm import tqdm


def save_txt(data, path):
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(data))

def load_txt(path):
    with open(path, "r", encoding="utf-8") as fp:
        data = fp.read().strip().split("\n")
    return data

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False)


def get_types():
    entity_types = set()
    relation_types = set()

    with open("duie_schema.json", "r", encoding="utf-8") as fp:
        schema = fp.read().strip().split("\n")
    for sche in schema:
        sche = sche.strip()
        sche = json.loads(sche)
        predicate = sche["predicate"]
        obj_type = sche["object_type"]["@value"]
        sbj_type = sche["subject_type"]
        if "人物" in obj_type:
            obj_type = "人物"
        if "人物" in sbj_type:
            sbj_type = "人物"
        entity_types.add(obj_type)
        entity_types.add(sbj_type)
        relation_types.add(predicate)

    entity_types.add("人物")
    print(list(entity_types))
    print(list(relation_types))
    save_txt(list(entity_types), "entity_types.txt")
    save_txt(list(relation_types), "relation_types.txt")


def process_entity(entity):
    entity = entity.replace("*", "\*")
    entity = entity.replace("(", "\(")
    entity = entity.replace(")", "\)")
    entity = entity.replace("+", "\+")
    entity = entity.replace(".", "\.")
    entity = entity.replace("?", "\?")
    entity = entity.replace("!", "\!")
    entity = entity.replace("[", "\[")
    entity = entity.replace("]", "\]")
    return entity


def get_conell04_data(in_path, out_path):
    with open(in_path, "r", encoding="utf-8") as fp:
        data = fp.read().strip().split("\n")
    res = []
    for d in tqdm(data, ncols=100):
        d = d.strip()
        d = json.loads(d)
        # pprint(d)
        text = d["text"]
        if len(text) > 256:
            continue
        # print(len(text))
        spo_list = d["spo_list"]
        tmp = {}
        tmp["tokens"] = [i for i in text]
        if len(tmp["tokens"]) == 0:
          continue
        tmp['entities'] = []
        tmp['relations'] = []
        # print(text)
        entity_tmp = []
        relation_tmp = []
        entity_set = []
        dict_to_ent_id = {}
        ent_id = 0
        for spo in spo_list:
            rel = spo["predicate"]
            obj_type = spo["object_type"]["@value"]
            if "人物" in obj_type:
                obj_type = "人物"
            sbj_type = spo["subject_type"]
            if "人物" in sbj_type:
                sbj_type = "人物"
            sbj = spo["subject"]
            obj = spo["object"]["@value"]
            if not sbj or not obj:
              continue
            sbj = process_entity(sbj)
            obj = process_entity(obj)
            # print(sbj)
            # print(obj)
            # print(text)
            try:
                sbj_re = re.search(sbj, text)
                obj_re = re.search(obj, text)
            except Exception as e:
                print(e)
                continue
            # print(sbj_re)
            # print(obj_re)

            if sbj_re:
                sbj_start = sbj_re.start()
                sbj_end = sbj_re.end()
                if (sbj_type, sbj_start, sbj_end) not in entity_set:
                    entity_set.append((sbj_type, sbj_start, sbj_end))
                    dict_to_ent_id[(sbj_type, sbj_start, sbj_end)] = ent_id
                    entity_tmp.append({"type": sbj_type, "start": sbj_start, "end": sbj_end, "ent_id": ent_id})
                    sbj_id = ent_id
                    ent_id += 1
                else:
                    sbj_id = dict_to_ent_id[(sbj_type, sbj_start, sbj_end)]

            if obj_re:
                obj_start = obj_re.start()
                obj_end = obj_re.end()
                if (sbj_type, obj_start, obj_end) not in entity_set:
                    entity_set.append((sbj_type, obj_start, obj_end))
                    dict_to_ent_id[(sbj_type, obj_start, obj_end)] = ent_id
                    entity_tmp.append({"type": obj_type, "start": obj_start, "end": obj_end, "ent_id": ent_id})
                    obj_id = ent_id
                    ent_id += 1
                else:
                    obj_id = dict_to_ent_id[(sbj_type, obj_start, obj_end)]
            relation_tmp.append({"type": rel, "head_id": sbj_id, "tail_id": obj_id})

        entity_tmp = sorted(entity_tmp, key=lambda x: x["start"])
        # print(entity_tmp, relation_tmp)
        for relation in relation_tmp:
            rel_head_id = relation["head_id"]
            rel_tail_id = relation["tail_id"]
            for i, entity in enumerate(entity_tmp):
                if rel_head_id == entity["ent_id"]:
                    relation["head"] = i
                if rel_tail_id == entity["ent_id"]:
                    relation["tail"] = i
        # print(relation_tmp)
        # print()
        # for relation in relation_tmp:
        #     print(relation)
        #     print(entity_tmp[relation["head"]])
        #     print(entity_tmp[relation["tail"]])
        #     print(text[entity_tmp[relation["head"]]["start"]:entity_tmp[relation["head"]]["end"]])
        #     print(text[entity_tmp[relation["tail"]]["start"]:entity_tmp[relation["tail"]]["end"]])
        #     print("="*100)
        for entity in entity_tmp:
            del entity["ent_id"]
        flag = False
        for relation in relation_tmp:
            if "head" not in relation or "tail" not in relation:
                flag = True
                break
            del relation["head_id"]
            del relation["tail_id"]
        if flag:
            continue
        tmp["entities"] = entity_tmp
        tmp["relations"] = relation_tmp
        res.append(tmp)
    # if "train" in out_path:
    #   res = res[20000:]
    # res = res[:10000]  # 这里设置取多少条数据
    save_json(res, out_path)

def get_duie_types():
    entities = load_txt("entity_types.txt")
    relations = load_txt("relation_types.txt")
    res = {}
    res["entities"] = {}
    res["relations"] = {}
    ent_tmp = {}
    rel_tmp = {}
    for ent in entities:
        ent_tmp[ent] = {"short": ent, "verbose": ent}
    for rel in relations:
        rel_tmp[rel] = {"short": rel, "verbose": rel, "symmetric": False}
    res["entities"] = ent_tmp
    res["relations"] = rel_tmp

    save_json(res, "duie_types.json")

def get_predict_example():
    text = "《废物小说》是新片场出品，杜煜峰（东北花泽类）导演2的动画首作，作品延续了他一贯的脱力系搞笑风格"
    res = []
    tokens = [i for i in text]
    tmp = {}
    tmp["tokens"] = tokens
    res.append(tmp)
    res.append(tokens)
    res.append(" ".join(tokens))
    print(res)
    save_json(res, "duie_prediction_example.json")
    return res

if __name__ == '__main__':
    get_types()
    get_conell04_data("duie_dev.json", "dev.json")
    get_conell04_data("duie_train.json", "train.json")
    get_duie_types()
    get_predict_example()