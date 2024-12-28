from moatless.agent.code_agent import CodingAgent
from moatless.agent.code_prompts import SIMPLE_CODE_PROMPT
from moatless.benchmark.swebench import create_repository
from moatless.benchmark.utils import get_moatless_instance
from moatless.completion import CompletionModel
from moatless.file_context import FileContext
from moatless.index import CodeIndex
from moatless.search_tree import SearchTree
from moatless.actions import FindClass, FindFunction, FindCodeSnippet, SemanticSearch, ViewCode, StringReplace, CreateFile, AppendString, RunTests, Finish, Reject
import os
import dotenv

dotenv.load_dotenv()

index_store_dir = "/tmp/index_store"
repo_base_dir = "/tmp/repos"
persist_path = "trajectory.json"

instance = get_moatless_instance("django__django-16379")

completion_model = CompletionModel(
    model="openai/accounts/fireworks/models/llama-v3p1-405b-instruct",
    temperature=0.0,
    model_base_url=os.getenv("CUSTOM_LLM_API_BASE"),
    model_api_key=os.getenv("CUSTOM_LLM_API_KEY")
)

repository = create_repository(instance)

code_index = CodeIndex.from_index_name(
    instance["instance_id"], index_store_dir=index_store_dir, file_repo=repository
)

actions = [
    FindClass(code_index=code_index, repository=repository),
    FindFunction(code_index=code_index, repository=repository),
    FindCodeSnippet(code_index=code_index, repository=repository),
    SemanticSearch(code_index=code_index, repository=repository),
    ViewCode(repository=repository),
    StringReplace(repository=repository, code_index=code_index),
    CreateFile(repository=repository, code_index=code_index),
    AppendString(repository=repository, code_index=code_index),
    RunTests(repository=repository, code_index=code_index),
    Finish(),
    Reject()
]

file_context = FileContext(repo=repository)
agent = CodingAgent(
    actions=actions,
    completion=completion_model,
    system_prompt=SIMPLE_CODE_PROMPT,

)

search_tree = SearchTree.create(
    message=instance["problem_statement"],
    agent=agent,
    file_context=file_context,
    max_expansions=1,
    max_iterations=50
)

node = search_tree.run_search()
print(node.observation.message)