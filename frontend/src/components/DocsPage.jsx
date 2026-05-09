function Section({ title, children }) {
  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5">
      <h2 className="text-lg font-bold text-gray-900 mb-2">{title}</h2>
      <div className="text-sm text-gray-700 leading-relaxed space-y-2">{children}</div>
    </section>
  )
}

function Tag({ children, tone = 'gray' }) {
  const tones = {
    gray: 'bg-gray-100 text-gray-600',
    green: 'bg-green-50 text-green-700',
    amber: 'bg-amber-50 text-amber-700',
    red: 'bg-red-50 text-red-700',
    indigo: 'bg-indigo-50 text-indigo-700',
  }
  return (
    <span className={`inline-block text-[11px] px-1.5 py-0.5 rounded font-medium ${tones[tone]}`}>
      {children}
    </span>
  )
}

export default function DocsPage({ onBack }) {
  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-5">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Operation Guide</h1>
            <p className="text-sm text-gray-600 mt-1">
              How BizQuery turns your CSVs and documents into safe, grounded answers.
            </p>
          </div>
          <button
            onClick={onBack}
            className="text-sm text-indigo-600 hover:text-indigo-700 whitespace-nowrap"
          >
            ← Back to workspace
          </button>
        </header>

        <Section title="The vision">
          <p>
            BizQuery is a focused workspace for business data. Pick what the
            assistant can see on the left, browse charts in the middle, and ask
            questions on the right. Every answer is grounded in <em>only</em> the
            sources you select — nothing else leaks in.
          </p>
        </Section>

        <Section title="Choosing datasets">
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Checkbox</strong> = include in chat. Tick multiple datasets and
              the assistant will reason across all of them.
            </li>
            <li>
              <strong>Click a row</strong> = focus its KPIs and charts in the middle
              panel.
            </li>
            <li>
              <strong>Select all</strong> in the section header toggles every dataset
              (or every ingested document) at once.
            </li>
            <li>
              Documents (PDF / TXT / MD) work the same way — chunked, embedded, and
              retrieved via semantic search when relevant to your question.
            </li>
          </ul>
        </Section>

        <Section title="Data privacy — datasets">
          <p>Every CSV column is tagged with one of four sensitivity levels:</p>
          <ul className="list-none pl-0 space-y-1.5">
            <li><Tag tone="green">public</Tag> — visible to everyone.</li>
            <li>
              <Tag tone="amber">internal</Tag> — hidden by default; toggle{' '}
              <strong>Admin mode</strong> in the bottom-left to reveal.
            </li>
            <li>
              <Tag tone="red">pii</Tag> / <Tag tone="red">identifier</Tag> — never
              shown, never charted, never sent to the LLM. The assistant deflects if
              asked.
            </li>
          </ul>
          <p>
            Only aggregate stats (sums, means, top slices) are sent to the model — raw
            rows never leave the backend. Policy is checked on every turn, so revoking
            access mid-conversation immediately blocks any further mention.
          </p>
        </Section>

        <Section title="Data privacy — documents">
          <p>Uploaded PDFs, TXTs, and MDs get the same two-tier gate as datasets:</p>
          <ul className="list-none pl-0 space-y-1.5">
            <li><Tag tone="green">public</Tag> — retrieved like any other document.</li>
            <li>
              <Tag tone="red">confidential</Tag> — tick <strong>Mark next upload
              confidential</strong> before adding the file. Its chunks are excluded
              from chat retrieval unless <strong>Admin mode</strong> is on, and the
              sidebar shows a red badge.
            </li>
          </ul>
          <p>
            On top of that, every chunk passes through a <strong>PII scrub</strong> at
            ingest time — emails, phone numbers, and SSNs are masked before the text
            is embedded. PII never reaches the vector store, the LLM, or chat
            history; even an admin viewing a confidential doc sees the redacted text.
          </p>
        </Section>

        <Section title="Metrics & charts">
          <p>
            KPIs and charts only render for <strong>recognized business metrics</strong>:
            USD, spend, revenue, budget, impressions, clicks, conversions, subscribers,
            votes, hours. Identifiers, ratings, and ages are skipped.
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Bar charts</strong> appear only when the top slice is at least
              1.5× the average — flat distributions are filtered out.
            </li>
            <li>
              <strong>Line charts</strong> require ≥3 time points and a coefficient of
              variation ≥5% — anything flatter is noise.
            </li>
            <li>USD-tagged columns auto-format as money ($3.56M, $12.4K, …).</li>
          </ul>
        </Section>

        <Section title="Asking good questions">
          <ul className="list-disc pl-5 space-y-1">
            <li>
              Ground questions in the data on screen. <em>“Which campaign drove the
              most spend last quarter?”</em> beats <em>“What should I do?”</em>.
            </li>
            <li>
              Mix sources freely — “compare revenue across the marketing and product
              datasets” works when both are checked.
            </li>
            <li>
              The assistant answers in 1–2 sentences and ends with one optional
              follow-up. Ask the follow-up if you want more.
            </li>
            <li>
              If a metric isn’t available, the assistant deflects rather than
              hallucinating — that’s by design.
            </li>
          </ul>
        </Section>

        <Section title="What makes this different">
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <Tag tone="indigo">Field-level policy</Tag> — privacy enforced per
              column, not per file.
            </li>
            <li>
              <Tag tone="indigo">Multi-source grounding</Tag> — chat answers can span
              several datasets and uploaded documents in one turn.
            </li>
            <li>
              <Tag tone="indigo">Signal-aware visuals</Tag> — charts only render when
              the data actually has a story; nothing flat or trivial.
            </li>
            <li>
              <Tag tone="indigo">Local RAG</Tag> — documents are embedded with ONNX
              and stored in ChromaDB; nothing leaves your machine until you ask a
              question.
            </li>
          </ul>
        </Section>
      </div>
    </div>
  )
}
