# 概念解释

## Knowledge Base / 知识库

不是“文件越多越好”的文件夹，而是一套可以长期查询、更新、追溯和复用的信息系统。

## Profile / 知识库配置档案

机器快速读取的设置表，默认 `.second-brain/profile.yaml`。

它记录平台、路径、写入模式、链接方式、来源规则、并发模式等参数。

## Structure Contract / 知识库结构与治理约定

人和 Agent 都能读懂的管理制度，默认 `.second-brain/structure-contract.md`。

它描述目录、命名、页面类型、索引、来源、归档和写入边界。

## Adaptive Structure / 自适应结构

已有知识库先理解再适配，不要求迁移到固定目录。

## Source Layer / 原始材料层

保留“原来到底是什么”的材料，例如 PDF、Word、会议原文、网页快照、聊天导出。

默认不可静默改写。

## Knowledge Layer / 知识层

AI 可以持续维护的知识页，用来表达“当前最可用版本”。

## Living Knowledge / 持续演进知识

知识页维护当前状态，不把每轮聊天都追加在末尾。

## Entity / 实体

现实中需要稳定识别的对象，例如人物、机构、产品、项目、业务线。

## Entity Resolution / 实体归一

判断不同名称是否指向同一个实体，例如正式名、简称、曾用名、公司主体名。

名字相同不代表一定同一实体，名字不同也不代表一定不同实体。

## Snapshot / 快照

带明确观察日期或统计期间的时效信息，例如价格、排名、粉丝数、项目状态。

## Source Fact / 来源事实

来源直接支持的事实。

## User Judgment / 用户判断

用户自己明确表达的判断，不应被伪装成客观事实。

## Agent Inference / Agent 推断

Agent 根据多个来源形成的分析，需要明确标识为推断。

## Decision / 用户决策

用户明确拍板的结论、状态或处理决定。

## Pending / 待核

当前无法确认或存在关键冲突的信息。

## Mutation / 写入变更

对知识库产生实际修改的动作。

五类核心判断：UPDATE、MERGE、CREATE、PENDING、SOURCE_ONLY。

## Governance / 治理

决定“知识库应该怎么被管理”的规则层，而不是业务知识本身。

## Multi-Agent Single Writer

多个 Agent 可以读同一个库，但同一时刻只允许一个写执行者，避免并发覆盖。
