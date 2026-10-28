# Local Workflow Exchange

This repository acts as a shared message board and staging area for local project automation. It is used to pass code snippets, error logs, and task notes between different processes running on the local machine.

## ⚠️ Security Notice
**Do not commit API keys, passwords, personal emails, phone numbers, or document IDs to this repository.** 
This repository is public and is not processed by the sanitization scripts. Keep all messages and code snippets free of sensitive data.

## 📁 Directory Structure

- `/from_claude/` - Incoming messages, error logs, and code snippets from the local builder process.
- `/to_claude/` - Outgoing responses, patches, and instructions from the review process.

## 🤖 Automation Rules

1. **Submitting a Request:**
   - Write the request to `from_claude/question.md`.
   - Include the target file path and the relevant code block.
   - Commit and push the file to GitHub.

2. **Processing the Response:**
   - Check for `to_claude/answer.md`.
   - Apply the provided patch to the local codebase and run tests.
   - Once successfully applied, clear `from_claude/question.md` to prepare for the next task.

## 👤 Manual Override (Human)

If the local automation script is paused:
- Manually copy the contents of `from_claude/question.md` into the AI chat interface.
- Paste the AI's response into `to_claude/answer.md` and push.
