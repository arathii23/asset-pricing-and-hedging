# Learn it from the basics

## First: what problem are we solving?

The finance dashboard contains numbers and terms a new visitor may not understand.
We already have explanations of those terms and the project's saved calculations.
The chatbot finds the right explanation and asks a local language model to make
it understandable. It is an **open-book tutor**, not a market forecaster.

## 1. What is a language model?

A language model predicts and generates text from a supplied input. Qwen has
already learned language during training by its publisher. We download its
existing weights and perform **inference**: using that trained model.

We are not training Qwen on our finance project. A small model can write plausible
but incorrect text. Giving it notes helps, but does not make it infallible.

## 2. Why not just send the question to Qwen?

It may know what a share is, but it cannot reliably know our exact experiment,
date, units or limitations. It might invent an answer. We supply relevant saved
project passages, rather than relying on its general knowledge.

We could send every note, but that increases input size and can distract a small
model. Retrieval selects a few relevant passages. For a tiny corpus, full-context
or keyword search is also a reasonable baseline; FAISS is useful here for learning
and inspection, not proof that the project needs a large vector database.

## 3. What is a chunk?

A chunk is a small piece of a document. Each one keeps the document title,
heading, version and source path. We split long sections and overlap a little
text so a boundary is less likely to cut away all useful context.

Models read **tokens**, not exactly words. One word can become several tokens.
The embedding model truncates long input, so we explicitly keep its inputs below
that limit. Headings count toward the budget. Overlap improves continuity but
does not guarantee every table row or explanation will fit in one passage.

## 4. What is an embedding?

MiniLM converts text into a list of 384 numbers: a vector. The list represents
features of the text's meaning, not a readable finance answer. We use the **same
model** for passages and questions so their vectors can be compared.

For example, “Why does the firm borrow?” and a note about company loans can have
similar embeddings even when their wording differs. Embeddings can also match
the wrong meaning. That is why you inspect retrieved notes and test retrieval.

## 5. What does FAISS do?

FAISS searches vectors. We normalise each vector to length one and use
`IndexFlatIP`: exact inner-product search. On normalised vectors, inner product
equals cosine similarity, a measure of direction similarity.

The largest score is the closest vector, **not the probability the answer is
correct**. We retrieve three different source sections. Before search, the index
contains only common notes and the selected research version.

## 6. Where does RAG happen?

Suppose the question is “What is a share?”

1. MiniLM embeds the question.
2. FAISS retrieves the ownership explanation, labelled `[S1]`.
3. We create a prompt containing the question, the source passage and instructions.
4. Qwen generates a short explanation and returns a JSON record with an answer
   and source IDs, such as `S1`. A fictional example demonstrates that format.
5. Python validates the fields and IDs, then shows the answer and source labels
   beside the actual source text. Bad formatting triggers a labelled fallback.

This format instruction is **prompting**, not training or fine-tuning. Valid JSON
is not proof of a correct answer: it just makes the response easier to validate.

The **retrieval** finds the book page. **Augmentation** adds it to the prompt.
**Generation** writes an answer. Without a language model generating an answer,
the same retrieval is document search, not a successful generative RAG response.

## 7. Is an embedding model also an LLM?

Both use neural-network language representations, but their jobs differ here.
MiniLM produces a fixed-size vector for search. Qwen generates an answer token
by token. FAISS does neither: it searches the stored vectors.

## 8. How can it handle “explain it simpler”?

That question alone does not identify the topic. For a short follow-up containing
words such as “it”, the app adds the previous user question to the search query.
That is a simple heuristic, not a sophisticated conversation-rewriting agent.
Previous generated answers are not used as factual source material. Changing
version resets the conversation to reduce cross-version confusion.

## 9. How do we know it works?

There are different questions to test:

- **Software:** Did version filtering, token limits and citation checks work?
- **Retrieval:** Was a relevant source among the three results?
- **Generation:** Did Qwen actually use that source correctly, with correct units?
- **Abstention:** Did it admit missing or live information rather than invent it?
- **Practicality:** How long did it take, and did it fit in the laptop's memory?

Passing the first two does not prove the third. A valid `[S1]` can be attached to
a false claim. Our reference evaluation is small and transparent, not a claim of
general model accuracy or eliminated hallucinations.

## Learning exercises

1. Ask “What is a share?”. Find the exact sentence supporting the answer.
2. Rephrase it as “What do I own when I buy company stock?”. Compare the scores.
3. Ask a finance question and an unrelated question. Compare retrieval relevance.
4. Ask about the original Sharpe, then switch to the review. Check source versions.
5. Compare lexical and semantic retrieval results in the evaluation report.
6. Try a larger model with the same evidence. Record factual differences and time;
   do not choose whichever answer sounds more confident.
7. Add a short, approved explanation, rebuild the index, and verify retrieval.
   Do not put credentials or instructions in searchable notes.

## A defensible interview explanation

Describe the actual work: a local finance tutor using a curated, versioned
knowledge base, MiniLM embeddings, exact FAISS search and Qwen generation, with
source inspection and separate retrieval/answer checks. Explain the design
choices and limitations. Do not claim model training, production security,
financial advice or a measured accuracy percentage that you have not evaluated.

The finance portfolio models (Ridge/gradient boosting) predict returns in a
separate historical experiment. They are not the chatbot's embedding or language
model. Finance ML and generative RAG share the project context but solve different
problems.
