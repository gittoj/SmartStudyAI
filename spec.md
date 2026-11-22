# SmartStudy AI

Product specification for the first version of the website.

## Context & Goal

SmartStudy AI is a website for parents of Singapore Primary 2, Primary 3, and Primary 4 children. The parent owns the account. After logging in, the parent creates a profile for each child, photographs or uploads that child's Mathematics or English worksheets, and uses a dashboard to see which topics the child understands. The site turns a worksheet into a short explanation, a small set of extra practice questions, and feedback after the child answers. The child selects their own profile and uses it to work through a hard topic, try similar questions, and see what went wrong. The point of the site is to cut down the time a parent spends making revision sheets, and to let the child practise with less hand-holding.

## Inputs & Outputs

All dates are ISO 8601 strings in UTC (`YYYY-MM-DDTHH:mm:ss.sssZ`). Identifiers are UUID v4 strings. Levels are Singapore primary levels only: `P2`, `P3`, `P4`. Subjects are `mathematics` and `english` only.

The Next.js app uses the TypeScript interfaces below. The FastAPI service uses Pydantic models with the same field names and enums. JSON field names stay camel case, matching these interfaces.

```ts
type Level = "P2" | "P3" | "P4";
type Subject = "mathematics" | "english";

type WorksheetStatus =
  | "uploaded"
  | "processing"
  | "ready"
  | "needs_review"
  | "failed";

type Mastery = "not_started" | "needs_practice" | "developing" | "confident";

type ReportReason = "answer_looks_wrong" | "dont_understand" | "something_else";

interface ParentAccount {
  id: string;
  email: string;
  displayName: string;
  createdAt: string;
}

interface ChildProfile {
  id: string;
  parentId: string;
  /** Unique among this parent's children. Stored in lowercase. */
  username: string;
  level: Level;
  createdAt: string;
}

interface WorksheetUpload {
  childId: string;
  subject: Subject;
  /** Optional. If omitted, the app infers a topic after reading the file. */
  topicHint?: string;
  fileName: string;
  mimeType: "application/pdf" | "image/jpeg" | "image/png" | "image/webp";
  /** Raw bytes, maximum 10 MB. */
  sizeBytes: number;
}

interface WorksheetPage {
  pageNumber: number;
  /** Text read from the page. Empty string if nothing readable was found. */
  extractedText: string;
  /** OCR confidence from 0 to 1. Null when text is extracted directly from a PDF text layer. */
  confidence: number | null;
}

interface WorkedExample {
  prompt: string;
  steps: string[];
  answer: string;
}

interface PracticeQuestion {
  id: string;
  prompt: string;
  /** Exactly four choices. V1 has no written-answer questions. */
  choices: [string, string, string, string];
}

interface WorksheetResult {
  id: string;
  childId: string;
  subject: Subject;
  level: Level;
  topic: string;
  status: WorksheetStatus;
  pages: WorksheetPage[];
  /** Two to five short sentences. Vocabulary matches the child's level. */
  explanation: string;
  workedExample: WorkedExample;
  practiceQuestions: PracticeQuestion[];
  parentNote: string;
  failureReason?: "unreadable" | "wrong_subject" | "too_long" | "unsupported_file" | "service_unavailable";
  createdAt: string;
}

interface PracticeAttempt {
  id: string;
  childId: string;
  worksheetId: string;
  questionId: string;
  answer: string;
  isCorrect: boolean;
  /** One or two sentences saying what to try next. No scores, ranks, or comparison with other children. */
  feedback: string;
  submittedAt: string;
}

interface TopicProgress {
  childId: string;
  subject: Subject;
  level: Level;
  topic: string;
  mastery: Mastery;
  questionsAttempted: number;
  questionsCorrect: number;
  lastPractisedAt: string | null;
}

interface ReportedQuestion {
  id: string;
  topic: string;
  prompt: string;
  choices: string[];
  correctChoice: string;
  explanation: string;
  reason: ReportReason;
  createdAt: string;
}

interface ParentDashboard {
  child: Pick<ChildProfile, "id" | "username" | "level">;
  topics: TopicProgress[];
  recentWorksheets: Array<
    Pick<WorksheetResult, "id" | "subject" | "topic" | "status" | "createdAt" | "parentNote" | "failureReason">
  >;
  reportedQuestions: ReportedQuestion[];
}
```
The frontend sends worksheet uploads using multipart/form-data. The file is sent as a binary file field, not as a JSON string. FastAPI receives it using UploadFile. The remaining fields (childId, subject, and optional topicHint) are sent as form fields.
Responses never include `passwordHash`, `pinHash`, `expectedAnswer` before submission, file bytes, or model prompts. A worksheet file is an input only. The durable outputs are `WorksheetResult`, `PracticeAttempt`, and `TopicProgress`.
AnswerKey is a backend-only data structure. The backend stores the correct answer and explanation securely and checks submitted answers server-side. It must never be included in frontend TypeScript interfaces or normal worksheet API responses. After submission, the API returns the correctness result, correct choice, and explanation.
Extracted worksheet text is an internal backend processing field. It must not be returned in normal parent or child API responses. Retain it internally only as needed for worksheet generation and the permitted retry.

## Behavior Rules

### Parent account

- The parent creates one account with an email, a display name, and a password, then logs in. The parent remains the owner of that account.
- The password is at least 10 characters. The API stores only a hash.
- A successful login sets an httpOnly parent session cookie. Uploads, child-profile changes, and the progress dashboard require this session.
- Logging out clears the parent session and any selected child profile.
- A parent session can read and change only its own children, worksheets, and progress.
- Failed logins are limited to 10 per email and 20 per IP address in 15 minutes, and sign-ups to 10 per IP address per hour. Beyond that the API returns 429: 'Too many tries. Please wait a few minutes and try again.' A successful login resets that email's count.

### Child profile

- Only a logged-in parent can create a child profile. The fields are a username, the child's level, and a 4-digit PIN.
- One parent may have one to four child profiles.
- A username is 3 to 20 characters, using letters, numbers, and underscores. The API stores it in lowercase. `Alex` and `alex` are the same username.
- The username must be unique among that parent's children. If it is already used there, show "That username is already used. Choose another one." and do not create a profile.
- The PIN is exactly four digits. The API stores only a hash.
- The child does not get an email or password. On the practice screen, the child selects their profile from the profiles this parent created and enters the PIN.
- A wrong PIN shows "That PIN is not right." Five wrong tries lock that profile for 15 minutes. The five-failed-attempt lockout must be enforced server-side and cannot be bypassed by refreshing the browser or changing the request.
- After the correct PIN, the child can read ready worksheets and submit practice answers for that profile only. The child cannot upload worksheets, edit profiles, or open the progress dashboard.
- Deleting a child profile deletes that child's worksheets from private storage, attempts, and progress. The parent must type the child's username to confirm.

### Upload validation

Accept a file only when all of the following are true:

- The logged-in parent owns `childId`.
- `subject` is `mathematics` or `english`.
- The file extension and detected file type both match `application/pdf`, `image/jpeg`, `image/png`, or `image/webp`.
- Size is 1 byte to 10 MB.
- A PDF has 1 to 10 pages.
- An image is a single page.
- The child has fewer than 20 worksheets still in `uploaded` or `processing`.

If validation fails, do not store the file and do not call PyMuPDF, the OCR service, or OpenAI. Return a single message:

| Condition | Message |
| --- | --- |
| Empty file | "This file is empty. Choose a worksheet photo or PDF." |
| Over 10 MB | "This file is larger than 10 MB. Take a closer photo or export a smaller PDF." |
| Wrong type | "Use a PDF, JPG, PNG, or WEBP worksheet." |
| PDF over 10 pages | "This PDF has more than 10 pages. Upload one worksheet at a time." |
| Too many in progress | "Please wait. This child already has worksheets being read." |
| Child does not belong to this parent | "That child profile could not be found." |

### Reading a worksheet

1. Save the file as private and set status to `uploaded`, then `processing`.
2. Read each page to text in the FastAPI service. Use PyMuPDF for a PDF that has a text layer. Use the OCR service for a photo, and for any PDF page that has no text layer. Keep a page image only long enough to read it.
3. A PyMuPDF page with a text layer is readable. An OCR page is readable only when its confidence is 0.6 or higher. If no page is readable, or the combined text is under 20 characters, set status to `needs_review` and skip OpenAI. Show: "We could not read this clearly. Upload a brighter, flatter photo."
4. If the text is clearly the other subject (for example an English comprehension uploaded as Mathematics), set status to `needs_review` and show: "This looks like {detected subject}, but it was uploaded as {chosen subject}. Change the subject or upload a different page."
5. Use a consistent topic name for the same subject and learning concept across worksheets. Group progress by child, subject and normalised topic name.
6. Write the explanation for the child's saved level:
   - P2: short sentences, everyday words, one idea at a time.
   - P3: short sentences plus one new term, defined immediately.
   - P4: still simple, with one extra step in the worked example.
7. Produce one worked example from the same topic, using new numbers or a new short passage. Do not copy a question from the uploaded page.
8. Produce five multiple-choice questions. Each question has exactly four choices, and `expectedAnswer` is one of those choices. Include a one- or two-sentence explanation. Do not ask the child to type an answer. Written-answer questions belong in a later version. Use new numbers or a new short passage. Do not copy a question from the uploaded page.
9. Set status to `ready`. Explanations, the worked example and practice questions come from one OpenAI request. If the reply breaks a rule (not valid JSON, wrong question count, a question without four different choices, a correct answer not among the choices, or a question that reuses the worked example), the service asks once more, telling the model why the first reply was rejected. Timeouts and API errors are not regenerated. If the second reply is also invalid, or any call fails or times out after 60 seconds (45 seconds for the second request), set status to failed, keep the file, and show: "We could not prepare this worksheet. Try again." The parent may retry once from the same file.  
10. A worksheet still uploaded or processing after 15 minutes (for example, the server restarted) is set to failed with the standard failed message. A background check runs when the server starts and every 5 minutes.
11. The parent can remove a failed or needs_review worksheet. This deletes its file and record. ready worksheets cannot be removed.

### Practice and feedback

- Invalid questions trigger the automatic regeneration above before the worksheet is set to failed.
- V1 practice is multiple choice only. A question without exactly four choices, or whose correct answer is not one of those choices, is invalid. If the five questions are not all valid, set the worksheet to `failed` and do not show a partial set.
- Show one question at a time. Hide `expectedAnswer` and `explanation` until the child submits.
- The child submits one of the four choices. A submission that is not one of those choices is rejected with "Choose an answer first." and is not stored.
- Feedback is immediate. The response returns `isCorrect`, the correct choice, and the question's simple explanation before the child continues.
- A correct choice sets `isCorrect` to true. The feedback names what the child chose, such as "You found the half by choosing the shape split into two equal parts."
- An incorrect choice sets `isCorrect` to false, shows the correct choice, and shows the explanation. It does not say "wrong", show a score, or compare the child with anyone else.
- Each question accepts one submission. Another submit returns the stored feedback and does not change progress.
- Mastery for a topic uses the latest 10 attempts in that topic, or all attempts if fewer than 10 exist:
  - `not_started`: no attempts
  - `needs_practice`: Less than 50% correct
  - `developing`: 50%–79% correct but does not yet meet the `confident` criteria
  - `confident`: 80% or more correct, with at least 5 attempts
- A new worksheet on the same topic does not reset mastery. New attempts are added to the same topic.
- After answering, the child can tap 'This question looks odd' and pick one of: the answer doesn't look right, I don't understand it, something else. There is no free text. Only answered questions can be reported, and repeating a report changes nothing.
- A reported question is left out of mastery and attempt counts at once. The parent sees it under 'Questions to check', with the prompt, choices, marked answer, explanation and reason. The parent chooses 'It's wrong, hide it' (stays excluded) or 'It's fine, count it' (counts again). Only that child's parent can resolve it.

### Parent dashboard

- Only the logged-in parent can open the dashboard. The default child is the most recently viewed profile.
- The parent can switch between their own children. List topics grouped by subject, then by mastery: `needs_practice`, `developing`, `confident`, `not_started`.
- A topic row shows the topic name, mastery, questions correct out of questions attempted, and the date of the last attempt. If there are no attempts, show "Not practised yet".
- Recent worksheets show the newest eight. A `processing` row says "Reading worksheet". A `needs_review` or `failed` row shows the parent message from the rules above and a button to upload again.
- The dashboard shows each child's username and level. It does not show another parent's children, class rank, or a percentage leaderboard.

### Fallback states

- No parent session: show the parent login screen.
- Logged in with no children: ask the parent to create a child profile with a username, level, and PIN.
- Practice screen with no selected child: show the parent's child profiles and ask the child to choose one.
- No worksheets yet: "Upload a Mathematics or English worksheet to start."
- Processing: the child screen shows "Your worksheet is being prepared" and does not show an empty question list as if practice were ready.
- `needs_review` and `failed`: the child does not see the broken result. The parent sees the message and the retry or re-upload action.
- Dashboard with no attempts: show the uploaded topics as `not_started` rather than an empty page.

## Constraints

### Tech stack

- Frontend: Next.js 16 (App Router) with React 19 and TypeScript in strict mode. The browser does not call the database, OpenAI, PyMuPDF, or the OCR service.
- Backend API: Python and FastAPI. Parent login, child profiles, uploads, worksheet status, practice, and the parent dashboard are FastAPI routes.
- Database: PostgreSQL for parent accounts, child profiles, worksheet records, attempts, and topic progress. Each child's username is unique within the parent's account.
- AI service: The OpenAI API is called only from FastAPI to generate the explanation, worked example, and five multiple-choice questions. Practice feedback is generated by the backend using the stored answer key and explanation. Submitting an answer does not trigger another OpenAI call.
- Document processing: PyMuPDF for PDF text. An OCR service for worksheet photos and for PDF pages that have no text layer.
- Worksheet files are stored by the API outside PostgreSQL. The database stores the storage key, not the file bytes.
- Python 3.11 or newer for the API. Node.js 20 LTS or newer for the Next.js app.

### Libraries

- FastAPI request and response bodies are Pydantic models that match the interfaces in Inputs & Outputs. Parse OpenAI JSON with those models before saving.
- The Next.js app checks API responses before rendering. It does not reimplement rules that FastAPI already enforces.
- Use a maintained password and PIN hashing library in the API. Hash with a slow hash. Do not write a custom hash.
- Detect file type from the bytes. Trust that result, not the file extension alone.
- Read PDFs with PyMuPDF. Do not add a second PDF library.
- Do not add a UI component kit or a client state-management library unless a later spec says to.
- Do not call OpenAI, PyMuPDF, or the OCR service from Next.js. The OpenAI API key and the OCR credentials stay in FastAPI environment variables.
- Do not send worksheet text, child names, or answers to an analytics or logging product. OpenAI and the OCR service are the only outside processors of worksheet text.

### Performance

- Upload validation responds within 2 seconds, excluding the parent's own network transfer.
- A worksheet of 10 pages either becomes `ready`, `needs_review`, or `failed` within 120 seconds.
- The parent dashboard and the child practice screen render from saved records. Opening them does not call OpenAI, PyMuPDF, or the OCR service.
- Practice feedback for one answer returns within 3 seconds.
- A parent may process at most two worksheets at the same time across all of their children.

### Security and privacy

- This product handles children's learning data. Collect only the parent email, parent display name, password hash, child username, level, PIN hash, worksheet, and practice answers.
- Do not ask for the child's full name, school, class, date of birth, or photograph of the child.
- Passwords and PINs are stored only as hashes.
- The parent session can read and change only that parent's children and worksheets. A selected child profile can submit practice only for itself.
- Worksheet files are private. Access is a short-lived URL or a same-origin download for the owning parent. Files are not public and are not indexed.
- Delete stored page images after a successful read. If status is `failed` or `needs_review`, keep the original file for 7 days so the parent can retry, then delete it.
- Log worksheet id, status, and error code. Do not log file contents, extracted text, model prompts, passwords, or PINs.
- Transport is HTTPS only in deployed environments.
- After a correct PIN, FastAPI creates a separate child session using a secure, httpOnly cookie.
- The session is associated with the authenticated parent and selected child.
- The child can access only their own ready worksheets and practice questions.
- The child session cannot access parent dashboard or account-management functions.
- Parent and child sessions are separate and never active together. A correct PIN ends the parent session on that browser (the parent area is locked), and a parent login ends any child session. The parent must log in again to reach the dashboard or uploads.
- Logging out clears the relevant session cookie.
- selecting a child ends the parent session on that device, and parent login ends the child session.
- Rate-limit records store only keyed hashes of the email or IP address and are deleted after 24 hours.

### Coding style

- TypeScript `strict` is on in the Next.js app. Do not use `any`. Prefer `unknown` and a parsed response at the API boundary.
- Python public functions and FastAPI routes use type hints. Pydantic models stay aligned with the TypeScript interfaces in this spec. Do not invent a second set of field names.
- FastAPI dependencies check the parent session, and the parent-child relationship, before reading or writing. Practice routes also check that the requested child is the selected profile.
- User-facing copy is plain English, short enough for a parent in a hurry. Do not show stack traces, status codes, or OpenAI errors on the page.
- Name functions for the action they perform: `createChildProfile` and `submitPracticeAnswer` in TypeScript, `create_child_profile` and `submit_practice_answer` in Python. Avoid abbreviations.
- Keep level wording in one place so P2, P3, and P4 explanations cannot drift between screens.

## Acceptance Criteria

1. A parent can create an account, log in, and remain the owner of that account. A logged-in parent can create a child profile with a username, a level from P2 to P4, and a 4-digit PIN.
2. The logged-in parent can upload a PDF, JPG, PNG, or WEBP Mathematics or English worksheet of at most 10 pages for a child they own, within the size limit. The child cannot upload.
3. Uploads that break the validation table are refused with the matching message, and no worksheet result is created.
4. A readable worksheet ends as `ready` and shows an explanation, one worked example, and five multiple-choice questions suited to the child's level. Each question has four choices, one correct answer, and a simple explanation.
5. An unreadable page or a subject mismatch ends as `needs_review` with the specified message, and the child is not given practice from that file.
6. An OpenAI timeout or API failure ends as `failed` with "We could not prepare this worksheet. Try again." One manual retry is available and reuses extracted text.
7. The child selects their profile, enters the PIN, and answers one multiple-choice question at a time. The correct answer and explanation stay hidden until submit. A typed answer is not accepted in this version.
8. Feedback appears immediately after submission and includes whether the choice was correct, the correct choice, and the simple explanation. A question accepts one submission.
9. Topic mastery changes only from that child's attempts, using the thresholds in Behavior Rules.
10. The logged-in parent can view progress for each of their children, including mastery, attempt counts, last practice date, and the eight newest worksheets.
11. A request cannot open another parent's child, worksheet, file, or attempts by changing an id. A duplicate username under the same parent is refused.
12. Stored files, logs, and API responses contain no password, PIN, OpenAI API key, OCR credential, or `expectedAnswer` before the child submits.
13. Dashboard and practice pages load from PostgreSQL through FastAPI and do not wait on OpenAI, PyMuPDF, or the OCR service.
14. With no child, no worksheet, or a worksheet still processing, the screen shows the fallback copy in Behavior Rules instead of a blank page.
15. A second invalid AI reply, not the first, is what sends a worksheet to failed.
16. After repeated failed logins the API returns 429, and a correct password does not bypass it during the window.
17. A reported question is excluded from progress until the parent dismisses the report, and another parent cannot see or resolve it.