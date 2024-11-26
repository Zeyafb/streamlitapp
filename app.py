import re
import os
import json
import streamlit as st
from pdfminer.high_level import extract_text


# ===================== Helper Functions ===================== #

def extract_pdf_text(pdf_path):
    """Extract and clean text from a PDF file."""
    raw_text = extract_text(pdf_path)
    return clean_text(raw_text)


def clean_text(text):
    """Clean raw text by removing unnecessary elements."""
    text = re.sub(r'Page \d+( of \d+)?', '', text)  # Remove 'Page N' patterns
    text = re.sub(r'[ \t]+', ' ', text)  # Remove excessive spaces and tabs
    text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())  # Remove blank lines
    return text.strip()


def split_questions(text):
    """Split text into questions based on headings like 'Question #[number]'."""
    pattern = r'(Question #\d+)'
    parts = re.split(pattern, text)
    questions = [
        {'heading': parts[i].strip(), 'content': clean_text(parts[i + 1]) if i + 1 < len(parts) else ''}
        for i in range(1, len(parts), 2)
    ]
    return questions


def parse_question_content(question):
    """Parse question content into body and answer options."""
    content = clean_text(question['content'])
    answer_start = re.search(r'\b[A-Z]\.\s', content)
    question_body = content[:answer_start.start()].strip() if answer_start else content
    answer_choices_text = content[answer_start.start():].strip() if answer_start else ''
    
    options = {}
    if answer_choices_text:
        answer_choices = re.split(r'(?=[A-Z]\.\s)', answer_choices_text)
        for choice in answer_choices:
            match = re.match(r'^([A-Z])\.\s(.*)', choice.strip(), re.DOTALL)
            if match:
                options[match.group(1)] = match.group(2).strip()
    return question_body, options


def read_answer_key(answer_key_path):
    """Read the answer key from a file."""
    answer_key = {}
    try:
        with open(answer_key_path, 'r', encoding='utf-8') as file:
            for line in file:
                match = re.match(r'^(\d+)\.\s*([A-Z](?:,\s*[A-Z])*)$', line.strip())
                if match:
                    question_number = int(match.group(1))
                    correct_answers = [ans.strip() for ans in match.group(2).split(',')]
                    answer_key[question_number] = correct_answers
    except FileNotFoundError:
        st.error(f"Answer key file not found: {answer_key_path}")
    return answer_key


def save_questions_to_json(questions_by_part, output_path):
    """Save questions to a JSON file."""
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(questions_by_part, file, indent=4, ensure_ascii=False)
    st.success(f"Questions saved to {output_path}")


def highlight_text(text, search_query):
    """Highlight search query in the given text."""
    escaped_query = re.escape(search_query)
    return re.sub(
        f"({escaped_query})",
        r"<span style='background-color: #f3f3f3; color: #333; padding: 2px; border-radius: 4px;'>\1</span>",
        text,
        flags=re.IGNORECASE
    )


def navigate_to_question(part_name, question_number):
    """Navigate to a specific question."""
    st.query_params = {'part': part_name, 'question': question_number}
    st.rerun()


# ===================== Main Application ===================== #

def main():
    st.title("Practice Exam Simulator")

    # Load questions from JSON
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(current_dir, 'questions_by_part.json')
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            questions_by_part = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Error loading questions file: {e}")
        return

    parts = list(questions_by_part.keys())
    if not parts:
        st.error("No parts found in the questions data.")
        return

    # Sidebar: Mode selection
    st.sidebar.header("Mode Selection")
    mode = st.sidebar.radio("Select Mode:", ("Exam Mode", "Practice Mode"))
    st.session_state["mode"] = mode

    # Sidebar: Search functionality
    st.sidebar.header("Search Questions")
    search_query = st.sidebar.text_input("Enter a keyword or phrase to search:")
    st.session_state["search_query"] = search_query

    # Search results
    if search_query:
        search_results, total_instances = search_questions(questions_by_part, search_query)
        display_search_results(search_results, total_instances)

    # Display flagged questions in the sidebar
    display_flagged_questions(parts, questions_by_part)

    # Create tabs for each part
    tabs = st.tabs(parts)
    for idx, tab in enumerate(tabs):
        part_name = parts[idx]
        with tab:
            handle_part(part_name, questions_by_part[part_name])


# ===================== Helper Functions for Main ===================== #

def search_questions(questions_by_part, search_query):
    """Search for questions containing the query."""
    search_results = []
    total_instances = 0
    for part_name, questions in questions_by_part.items():
        for question in questions:
            occurrences = count_occurrences(question, search_query)
            if occurrences > 0:
                total_instances += occurrences
                search_results.append(format_search_result(part_name, question, search_query))
    return search_results, total_instances


def count_occurrences(question, search_query):
    """Count occurrences of the query in question text and options."""
    text_occurrences = len(re.findall(re.escape(search_query), question['question_text'], re.IGNORECASE))
    option_occurrences = sum(len(re.findall(re.escape(search_query), opt, re.IGNORECASE)) for opt in question['options'].values())
    return text_occurrences + option_occurrences


def format_search_result(part_name, question, search_query):
    """Format a question result with highlighted search query."""
    return {
        'part_name': part_name,
        'question_number': question['question_number'],
        'question_text': highlight_text(question['question_text'], search_query),
        'options': {k: highlight_text(v, search_query) for k, v in question['options'].items()}
    }


def display_search_results(search_results, total_instances):
    """Display search results."""
    st.sidebar.write(f"Found {len(search_results)} questions with {total_instances} occurrences.")
    for result in search_results:
        st.markdown(f"**Part:** {result['part_name']}, **Question {result['question_number']}**")
        st.markdown(result['question_text'], unsafe_allow_html=True)
        for option, option_text in result['options'].items():
            st.markdown(f"- **{option}**: {option_text}", unsafe_allow_html=True)


def display_flagged_questions(parts, questions_by_part):
    """Display flagged questions in the sidebar."""
    st.sidebar.header("Flagged Questions")
    any_flagged = False
    for part_name in parts:
        flagged = st.session_state.get(part_name, {}).get('flagged', set())
        if flagged:
            any_flagged = True
            st.sidebar.write(f"**{part_name}:**")
            for q_num in sorted(flagged):
                if st.sidebar.button(f"Go to {part_name} Q{q_num}", key=f"flagged_{part_name}_{q_num}"):
                    navigate_to_question(part_name, q_num)
    if not any_flagged:
        st.sidebar.write("No flagged questions.")


def handle_part(part_name, questions):
    """Handle questions for a specific part."""
    session_state = st.session_state.setdefault(part_name, {'current_question': 0, 'answers': {}, 'flagged': set()})
    total_questions = len(questions)

    if session_state.get('show_results', False):
        display_results(questions, session_state)
    else:
        display_question(part_name, questions, session_state, total_questions)


def display_question(part_name, questions, session_state, total_questions):
    """Display the current question."""
    current_index = session_state['current_question']
    question = questions[current_index]
    st.subheader(f"Question {current_index + 1} of {total_questions}")
    st.write(question['question_text'])
    # Add navigation and answer selection
    # ...


def display_results(questions, session_state):
    """Display results after the exam."""
    correct_count = sum(1 for q in questions if set(session_state['answers'].get(q['question_number'], [])) == set(q['correct_answer']))
    total_questions = len(questions)
    st.write(f"Your score: {correct_count}/{total_questions} ({(correct_count / total_questions) * 100:.2f}%)")


if __name__ == "__main__":
    main()
