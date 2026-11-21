import type { Mastery, TopicProgress } from "@/lib/types";

const MASTERY_LABEL: Record<Mastery, string> = {
  needs_practice: "Needs practice", developing: "Developing", confident: "Confident", not_started: "Not started",
};

export function TopicProgressList({ topics }: { topics: TopicProgress[] }) {
  if (topics.length === 0) return <p>Upload a Mathematics or English worksheet to start.</p>;
  return (
    <ul>
      {topics.map((topic) => (
        <li key={`${topic.subject}-${topic.topic}`}>
          <strong>{topic.topic}</strong> — {MASTERY_LABEL[topic.mastery]}
          {" "}
          {topic.questionsAttempted === 0
            ? "Not practised yet"
            : `${topic.questionsCorrect} of ${topic.questionsAttempted} correct, last practised ${new Date(topic.lastPractisedAt ?? "").toLocaleDateString()}`}
        </li>
      ))}
    </ul>
  );
}
