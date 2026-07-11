"""Honest multi-turn intake eval: a NON-LEAKY simulated user.

The earlier harness let the persona volunteer the gold parameter ("try 3 sigmas"),
which handed retrieval the anchor and inflated grounding. A real user asking "how many
should I pick?" does not know the GEM-pRF parameter name -- that's why they're asking.

This persona describes only its goal / data / constraints in plain experimental terms,
answers ONLY what is asked, and never names a GEM-pRF parameter or a numeric config value.
So grounding must come from the intake gathering genuinely useful context, not from leakage.

Captures the full transcript and the real final answer, and classifies each answer as
refusal / parameter-matrix / substantive so we can read results honestly. Runs on the live
engine (connect to the running weaviate holder in local mode).

Usage:  GEMPRF_ASSISTANT_WEAVIATE_MODE=local ... python scripts/eval_clarification_nonleaky.py [ids...]
"""
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from langchain_core.prompts import ChatPromptTemplate

from gemprf_assistant.rag.engine import GraphRagEngine
from gemprf_assistant.clarification import answer_with_clarification, is_unanswered, _MATRIX_PREFIX
from gemprf_assistant.rag.prompts import INSUFFICIENT_EVIDENCE_MESSAGE

GOLD = "datasets/clarification_intake_gold.jsonl"

PERSONA = (
    "You are a neuroimaging researcher using GEM-pRF for population receptive field mapping. "
    "You are a USER asking for help, NOT the assistant.\n"
    "Your situation: {goal}.\n"
    "Rules for every reply:\n"
    "- Answer ONLY the specific question the assistant just asked. Do not add extra information.\n"
    "- Speak in plain experimental terms: your task, stimulus, brain regions, data size, hardware, goals.\n"
    "- You do NOT know GEM-pRF's parameter/setting names or their numeric values -- that is exactly "
    "what you are trying to find out. NEVER name a parameter, setting, or a specific number.\n"
    "- If the assistant asks which parameter/setting/number you mean, say you don't know -- that's "
    "what you're asking them.\n"
    "- Keep replies under 15 words. Be a plausible, cooperative but non-expert user."
)


def classify(final):
    ans = (final.answer or "").strip()
    if getattr(final, "status", "") == "mechanism":
        return "mechanism"
    if not is_unanswered(final):
        return "substantive"
    if ans.startswith(_MATRIX_PREFIX):
        return "parameter_matrix"
    if ans == INSUFFICIENT_EVIDENCE_MESSAGE:
        return "refusal"
    return "other_ungrounded"


def run_case(engine, llm, item):
    q = item["question"]
    persona = PERSONA.format(goal=item["goal"])
    convo = [("user", q)]
    last = {"q": None}

    def output_fn(s):
        marker = "I need a bit more to answer that. "
        if marker in s:
            last["q"] = s.split(marker, 1)[1].strip()
            convo.append(("assistant", last["q"]))

    def input_fn(_p):
        hist = "\n".join(f"{r}: {t}" for r, t in convo)
        msgs = ChatPromptTemplate.from_messages([
            ("system", persona),
            ("human", "Conversation so far:\n{h}\n\nAssistant asks: {q}\nYour short reply:"),
        ]).format_messages(h=hist, q=last["q"])
        reply = str(llm.invoke(msgs).content).strip().strip('"')
        convo.append(("user_reply", reply))
        return reply

    final = answer_with_clarification(engine, q, input_fn=input_fn, output_fn=output_fn)
    rounds = sum(1 for r, _ in convo if r == "assistant")
    return {
        "id": item["id"], "question": q, "goal": item["goal"], "key_param": item["reveal"],
        "rounds": rounds, "grounded": not is_unanswered(final),
        "answer_class": classify(final), "transcript": convo, "final_answer": final.answer,
    }


def main():
    gold = [json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip()]
    if len(sys.argv) > 1:
        want = set(sys.argv[1:])
        gold = [g for g in gold if g["id"] in want]
    engine = GraphRagEngine()
    llm = engine.llm
    rows = []
    try:
        for item in gold:
            row = run_case(engine, llm, item)
            rows.append(row)
            print("\n" + "#" * 80)
            print(f"# {row['id']}  goal: {row['goal']}")
            print(f"# rounds={row['rounds']}  grounded={row['grounded']}  class={row['answer_class']}")
            print("#" * 80)
            for r, t in row["transcript"]:
                tag = {"user": "USER", "assistant": "ASSISTANT-ASKS", "user_reply": "USER-REPLY"}[r]
                print(f"  {tag:>14}: {t}")
            print(f"  {'FINAL-ANSWER':>14}: {row['final_answer'][:600]}")
            sys.stdout.flush()
    finally:
        engine.close()

    os.makedirs("results", exist_ok=True)
    with open("results/clarification_nonleaky_eval.json", "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)

    n = len(rows)
    print("\n" + "=" * 80)
    print(f"SUMMARY  n={n}")
    from collections import Counter
    print("  answer class:", dict(Counter(r["answer_class"] for r in rows)))
    print("  rounds dist :", dict(Counter(r["rounds"] for r in rows)))
    print(f"  substantive answers: {sum(1 for r in rows if r['answer_class']=='substantive')}/{n}")
    print(f"  multi-step (>=2 rounds): {sum(1 for r in rows if r['rounds']>=2)}/{n}")
    print("wrote results/clarification_nonleaky_eval.json")


if __name__ == "__main__":
    main()
