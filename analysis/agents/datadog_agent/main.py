from langchain_aws import ChatBedrockConverse
from langchain.agents import (
    create_react_agent,
    AgentExecutor,
)
from langchain import hub
from dotenv import load_dotenv
import os

from langchain_core.prompts import PromptTemplate

from analysis.agents.datadog_agent.context_injector import ContextInjector
from tools import get_tools

load_dotenv()


def lookup():
    llm = ChatBedrockConverse(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        temperature=0,
    )
    template = """
    You are a helpful assistant that can answer questions from the user by retrieving logs from datadog and analyzing them. Your answer must be precise and concise. 

    User Prompt: {user_prompt}
    Feature: {feature_name}
    Scenario: {scenario_name}
    Relevant microservices: {microservices}
    Examples of successful runs: {successful_runs}
    
    Use the provided context to better understand the system behavior and compare against the successful runs when analyzing.
    """
    prompt_template = PromptTemplate.from_template(template)
    tools = get_tools()
    react_prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, react_prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Elephant Flows Enhanced scenario
    timestamp_to_analyze = "2025-07-27T17:45:31Z"
    user_prompt = f"What happened in the ELEPHANTFLOW_ENHANCED scenario of the 100_ElephantFlows feature that happened in device id c5d308c8-3168-11f0-bd43-f2c0a0fdf6a8 for tenant ID af5f6035-7538-4709-b073-7b5f4b69543c around {timestamp_to_analyze}"

    # # Elephant Flows Legacy scenario
    # timestamp_to_analyze = "2025-07-27T17:53:38Z"
    # user_prompt = f"What happened in the ELEPHANTFLOW_LEGACY scenario of the 100_ElephantFlows feature that happened in device id c59d1eba-3169-11f0-bd43-f2c0a0fdf6a8 for tenant ID af5f6035-7538-4709-b073-7b5f4b69543c around {timestamp_to_analyze}"

    # Initialize context injector and inject context
    context_injector = ContextInjector()
    context = context_injector.inject_context(user_prompt)

    # Format the prompt with all context
    formatted_input = prompt_template.format_prompt(
        user_prompt=user_prompt,
        feature_name=context["feature_name"],
        scenario_name=context["scenario_name"],
        microservices=context["microservices"],
        successful_runs=context["successful_runs"],
    )

    result = agent_executor.invoke(input={"input": formatted_input})
    print(result["output"])


if __name__ == "__main__":
    lookup()
