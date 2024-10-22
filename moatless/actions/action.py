import importlib
import logging
from abc import ABC
from typing import List, Type, Tuple, Any, Dict

from pydantic import BaseModel, ConfigDict

from moatless.actions.model import ActionArguments, Observation
from moatless.file_context import FileContext
from moatless.index import CodeIndex
from moatless.repository.repository import Repository
from moatless.value_function.model import RewardScaleEntry

logger = logging.getLogger(__name__)


class Action(BaseModel, ABC):
    args_schema: Type[ActionArguments]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **data):
        super().__init__(**data)

    def execute(
        self, args: ActionArguments, file_context: FileContext
    ) -> Observation:
        """
        Execute the action.
        """

        message = self._execute(file_context=file_context)
        return Observation.create(message)

    def _execute(self, file_context: FileContext) -> str | None:
        """
        Execute the action and return the updated FileContext.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def get_evaluation_criteria(self, trajectory_length) -> List[str]:
        if trajectory_length < 3:
            return [
                "Exploratory Actions: Recognize that initial searches and information-gathering steps are essential and should not be heavily penalized if they don't yield immediate results.",
                "Appropriateness of Action: Evaluate if the action is logical given the agent's current knowledge and the early stage of problem-solving.",
            ]
        else:
            return [
                "Solution Quality: Assess the logical changes, contextual fit, and overall improvement without introducing new issues.",
                "Progress Assessment: Evaluate the agent's awareness of solution history, detection of repetitive actions, and planned next steps.",
                "Repetitive Actions: Detect if the agent is repeating the same unsuccessful actions without making progress and penalize accordingly.",
            ]

    def get_reward_scale(self, trajectory_length) -> List[RewardScaleEntry]:
        return [
            RewardScaleEntry(
                min_value=75,
                max_value=100,
                description="The action significantly advances the solution.",
            ),
            RewardScaleEntry(
                min_value=50,
                max_value=74,
                description="The action contributes positively towards solving the problem.",
            ),
            RewardScaleEntry(
                min_value=25,
                max_value=49,
                description="The action is acceptable but may have some issues.",
            ),
            RewardScaleEntry(
                min_value=0,
                max_value=24,
                description="The action has minimal impact or minor negative consequences.",
            ),
            RewardScaleEntry(
                min_value=-49,
                max_value=-1,
                description="The action is inappropriate or shows a lack of progress.",
            ),
            RewardScaleEntry(
                min_value=-100,
                max_value=-50,
                description="The action is counterproductive or demonstrates persistent repetition without learning.",
            ),
        ]

    @staticmethod
    def generate_reward_scale_entries(
        descriptions: List[Tuple[int, int, str]],
    ) -> List[RewardScaleEntry]:
        """
        Generate a list of RewardScaleEntry objects based on the provided descriptions.

        Args:
            descriptions: A list of tuples, each containing (min_value, max_value, description)

        Returns:
            A list of RewardScaleEntry objects
        """
        return [
            RewardScaleEntry(min_value=min_val, max_value=max_val, description=desc)
            for min_val, max_val, desc in descriptions
        ]

    def get_reward_range(self, trajectory_length: int) -> Tuple[int, int]:
        """
        Get the minimum and maximum reward values for this action.

        Args:
            trajectory_length: The length of the current trajectory

        Returns:
            A tuple containing the minimum and maximum reward values
        """
        reward_scale = self.get_reward_scale(trajectory_length)
        min_reward = min(entry.min_value for entry in reward_scale)
        max_reward = max(entry.max_value for entry in reward_scale)
        return min_reward, max_reward

    def get_value_function_prompt(self) -> str:
        """
        Get the base prompt for the value function.
        This method can be overridden in subclasses to provide action-specific prompts.
        """
        return """Your role is to evaluate the **last executed action** of the search tree that our AI agents are traversing, to help us determine the best trajectory to solve a programming issue. The agent is responsible for identifying and modifying the correct file(s) in response to the problem statement.

At this stage, the agent is still working on the solution. Your task is twofold:
1. **Evaluation**: Assess whether the change done by the **last executed action** is appropriate for addressing the problem and whether the agent is on the right path to resolving the issue.
2. **Alternative Feedback**: Independently of your evaluation, provide guidance for an alternative problem-solving branch. This ensures parallel exploration of different solution paths.
"""

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        dump = {
            "action_class": f"{self.__class__.__module__}.{self.__class__.__name__}"
        }
        dump.update(super().model_dump(**kwargs))
        dump.pop("args_schema", None)
        return dump

    @classmethod
    def model_validate(cls, obj: Any, repository: Repository = None, runtime: Any = None, code_index: CodeIndex = None) -> "Action":
        if isinstance(obj, dict):
            obj = obj.copy()
            obj.pop("args_schema", None)
            action_class_path = obj.pop("action_class", None)
            if action_class_path:
                module_name, class_name = action_class_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                action_class = getattr(module, class_name)

                if hasattr(action_class, "_repository") and hasattr(action_class, "_code_index") and hasattr(action_class, "_runtime"):
                    if repository is not None:
                        obj.pop("repository", None)
                    if code_index is not None:
                        obj.pop("code_index", None)
                    if runtime is not None:
                        obj.pop("runtime", None)
                    
                    # Use provided values, falling back to serialized values if not provided
                    return action_class(
                        repository=repository or obj.get("repository"),
                        code_index=code_index or obj.get("code_index"),
                        runtime=runtime or obj.get("runtime"),
                        **obj
                    )
                
                return action_class(**obj)
        return super().model_validate(obj)
