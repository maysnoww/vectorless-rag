import os
from datetime import datetime
from config import LOG_DIR


class QueryLogger:
    """Log the full processing pipeline for each query"""

    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.session_file = os.path.join(
            LOG_DIR,
            f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        self._write(f"# Query Log {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    def log_question(self, question, segments_count):
        self._write(f"---\n\n## Question: {question}\n\n")
        self._write(f"- Time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}\n")
        self._write(f"- Segments: {segments_count}\n\n")

    def log_retrieve_result(self, segment, result, request_elapsed, batch_elapsed, error=None, timing=None):
        status = "relevant" if result and result.get('relevant') else "not relevant" if result else "failed"
        self._write(f"### {segment['file']} ({segment['segment']})\n\n")
        self._write(f"- Status: {status}\n")
        self._write(f"- Request elapsed: {request_elapsed:.1f}s\n")
        self._write(f"- Batch elapsed: {batch_elapsed:.1f}s\n")
        if timing:
            self._write(f"- Sent: {timing['send_time']}\n")
            self._write(f"- First byte: {timing['first_byte_time']}\n")
            self._write(f"- Complete: {timing['complete_time']}\n")
        if result and result.get('relevant'):
            self._write(f"- Findings: {result.get('findings', '')}\n")
            self._write(f"- Quote: {result.get('quotes', '')}\n")
        if error:
            self._write(f"- Error: {error}\n")
        self._write("\n")

    def log_summary(self, answer, total_elapsed):
        self._write(f"### Summary\n\n")
        self._write(f"- Summary time: {total_elapsed:.1f}s\n\n")
        self._write(f"{answer}\n\n")

    def _write(self, text):
        with open(self.session_file, 'a', encoding='utf-8') as f:
            f.write(text)
