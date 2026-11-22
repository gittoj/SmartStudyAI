import type { Mastery, Subject, TopicProgress } from "@/lib/types";

const MASTERY_LABEL: Record<Mastery, string> = {
  needs_practice: "Needs practice", developing: "Developing", confident: "Confident", not_started: "Not started",
};
const SUBJECT_LABEL: Record<Subject, string> = { mathematics: "Mathematics", english: "English" };

export function TopicProgressList({ topics }: { topics: TopicProgress[] }) {
  if (topics.length === 0) return <p>Upload a Mathematics or English worksheet to start.</p>;
  const subjects = Array.from(new Set(topics.map((topic) => topic.subject)));
  return (
    <>
      {subjects.map((subject) => (
        <section key={subject} className="card">
          <h2 style={{ marginTop: 0 }}>{SUBJECT_LABEL[subject]}</h2>
          <ul className="rows">
            {topics.filter((topic) => topic.subject === subject).map((topic) => (
              <li key={topic.topic}>
                <span><span className="cap">{topic.topic}</span><br />
                  <span className="muted">{topic.questionsAttempted === 0 ? "Not practised yet"
                    : `${topic.questionsCorrect} of ${topic.questionsAttempted} correct · last practised ${new Date(topic.lastPractisedAt ?? "").toLocaleDateString()}`}
                  </span></span>
                <span className={`badge ${topic.mastery}`}>{MASTERY_LABEL[topic.mastery]}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}
