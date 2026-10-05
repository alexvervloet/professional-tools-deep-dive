# Chapter 5 verdict: LangGraph vs the hand-rolled agent loop

Written from real runs on 2026-07-14 (langgraph 1.2.9, langchain-openai
1.3.5; gpt-4o-mini at temperature 0; five tasks × two reps per
implementation, identical tool functions). Reproduce with
`secrun python ch05-langgraph/compare.py`.

> **Model note (2026-08-08).** These numbers were measured on `gpt-4o-mini`,
> which was this repo's default at the time. The code has since moved to
> `gpt-5.4-nano` and then, when nano was deprecated, to `gpt-6-luna` (with
> reasoning switched off), so re-running now won't reproduce these figures exactly.
> The verdict is deliberately left as measured rather than rewritten: the
> comparison it records really happened, on the models named above. What
> should survive a model change is the *shape* of each finding, and checking
> whether it does is a better exercise than trusting a refreshed number.

## The headline is a tie, and the tie is the lesson

Both implementations: **10/10 tasks, 2.0 LLM calls per task, 1.0 tool calls
per task, ~1.5s per task.** Not approximately the same: the same, run for
run, including the trap task (a denied save reported honestly, no file
written) and the efficiency task (no wasted tool call on a question that
needed none). The agent's competence lives in the model and the tool
descriptions, which were identical; the harness just routes messages. A
framework doesn't make an agent smarter, and at this scale (three tools,
single process, short tasks) it doesn't make it faster or cheaper either.
The 2026 framework wars aren't about what this chapter measured, which is
exactly why this chapter measured it.

## Where they actually differ: the shape of the pause

The one feature that forced different *architecture* was human-in-the-loop
approval:

- **Hand-rolled**: a callback inside the loop. Deny it and the denial
  becomes a tool result in the same run, same process, same stack frame.
  Twelve lines; can't survive a process restart.
- **LangGraph**: `interrupt()` inside the tool. The graph **stops**,
  checkpoints its state, and returns an `__interrupt__` marker; a second
  `invoke(Command(resume=...))`, seconds or days later, from the same or
  (with a persistent checkpointer) a different process, picks up exactly
  where it paused. The price of that durability shows up even in this demo:
  a checkpointer, a `thread_id` per conversation, and a resume loop in the
  caller.

Same product feature, two different claims: "I can ask before acting" vs
"I can *wait* before acting." If approvals in your product take days and
must survive deploys, the second claim is the one you need, and hand-rolling
it means building checkpointing yourself; that's the honest pro-LangGraph
case, and it has nothing to do with task success rates.

## The churn arrived mid-chapter

On its very first run, the port emitted:
`create_react_agent has been moved to langchain.agents ... Deprecated in
LangGraph V1.0, to be removed in V2.0.` The canonical way to build the
canonical agent moved to a **different package** (one this venv doesn't
even have installed) between the tutorials everyone learned from and the
version pinned here. The code keeps the old import; it works on the pinned
version, and the warning is left visible in with_tool.py's run on purpose
(compare.py silences it, pointing here). This is ch03's "defaults have a
vintage" lesson in agent form: framework knowledge depreciates; the loop
you wrote by hand doesn't.

**And it arrived again after the chapter shipped (2026-10-05).** The graph
started crashing on task 0 while the loop kept passing. The model's first
calculator call is `"12.5% of 480 + 17"`, which isn't valid arithmetic, so the
tool raises. The loop's `try/except` hands that error back as the tool result
and the model retries with a valid expression. LangGraph's prebuilt tool node
used to do the same. In the pinned langgraph (1.2.11, prebuilt 1.1.0), its
default only catches bad tool *arguments* and re-raises everything else, so the
whole run died with a `SyntaxError`, 3 runs out of 3, on any model. The fix is
one argument, `ToolNode(..., handle_tool_errors=True)`, and the point is that it
has to be written down: the behavior the tie above depended on was a default,
and defaults are what change between versions.

Dependency surface, for the record: the baseline is ~130 lines on the
OpenAI SDK alone; the port adds langgraph, langgraph-checkpoint,
langgraph-prebuilt, langchain-core, langchain-openai, and langsmith to the
tree: a tracing vendor's SDK arriving as a transitive dependency is its
own small lesson in where frameworks point.

## When you'd pick which

Hand-roll at this chapter's scale: the loop is a page, debuggable with a
print statement, and behaviorally indistinguishable, as measured. Reach
for LangGraph when you need what the tie *didn't* test: durable
checkpoint/resume across processes, long-lived human approvals, streaming
node-by-node events, or multi-agent graphs with shared state. Those are
real (they're why the enterprise deployment lists are real); just don't
credit them to the loop, and budget for the API surface moving under you 
it did, mid-chapter.

## The interview sentence

"I ran the same five-task eval over my hand-written agent loop and
LangGraph's prebuilt agent with identical tools: dead tie on success,
steps, and latency: the model is the agent; the harness routes messages
so I choose a framework for durable interrupts, checkpointing, and
orchestration, not for 'better agents,' and I pin versions because the
canonical entry point deprecated itself while I was writing the
comparison."
