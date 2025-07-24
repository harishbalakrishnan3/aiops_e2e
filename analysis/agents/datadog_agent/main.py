from langchain_aws import ChatBedrockConverse
from langchain.agents import (
    create_react_agent,
    AgentExecutor,
)
from langchain import hub
from dotenv import load_dotenv
import os

from langchain_core.prompts import PromptTemplate

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
    """
    prompt_template = PromptTemplate.from_template(template)
    tools = get_tools()
    react_prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, react_prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    user_prompt = "Were there any elephant flows in the last 12 hours for tenant ID af5f6035-7538-4709-b073-7b5f4b69543c? Keywords: elephant"
    # user_prompt = "Were there any errors in the last 12 hours for tenant ID af5f6035-7538-4709-b073-7b5f4b69543c?"
    result = agent_executor.invoke(
        input={"input": prompt_template.format_prompt(user_prompt=user_prompt)}
    )
    print(result["output"])


if __name__ == "__main__":
    lookup()
