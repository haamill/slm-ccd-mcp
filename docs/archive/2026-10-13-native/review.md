# 独立审查与修复记录

审查范围 c93d311..6319b79。唯一独立审查代理读取设计、计划、ledger、实现、测试及厂家Python包装；只读fake/mock复现，不操作真实设备，不读取凭据。原结论 With fixes。

| 原级别 | 发现 | 处理与验证 |
|---|---|---|
| Important | capture UUID目录junction或资产元数据/数据链接可能越过固定根目录，且metadata读取发生在校验前 | 共享confined_path先resolve并与启动时固定root比较；Windows真实junction测试先失败再通过，metadata read未触发；file symlink权限不足跳过 |
| Important | 一个SLM close失败跳过其余角色并丢失跟踪 | 独立逐角色close，确认成功后移除；收集角色错误；全量shutdown仍终止owner并重试清理；fake双屏故障测试红→绿 |
| Important | 仅目标矩形存在不足以检测完整拓扑/身份变化 | 保存完整Win32 active topology及monitor interface ID；connect之前及周期健康检查比较，变化锁存requires-rebind；不再枚举SDK；增加显示器/同矩形换身份测试红→绿 |
| Important | hardware提交后finish和fail均写入失败，结构化结果被第二异常覆盖 | 最后写入异常受保护，返回operation_id、stage、submitted及journal_failure uncertain结果；内存缓存和既有intent禁止同ID重放；测试红→绿 |
| Important | 已error或队列已锁存错误的CCD未在joint修改前拒绝 | adapter统一capture readiness，状态与队列错误预检；执行时再次检查；两个错误场景测试红→绿 |
| Important | journal只保存hash，无法追溯命令和参数 | SQLite兼容迁移增加params/steps；保存开始/完成记录，连接显式关闭；重启读取原参数和步骤测试红→绿 |
| Minor→Important | SLM1公开默认10bit，使普通8bit工作流失败 | 按角色/配置解析省略位深；显式声明仍检查；load和uniform默认8bit测试红→绿 |
| Minor→Important | 巨大但有限phi0转int64溢出，静默错误光栅 | phi0先按2π约简再加空间相位和量化；开启numpy invalid/over raise的独立周期预期测试红→绿 |

按实际影响重新定级：最后两项分别阻断正常振幅工作流、静默产生错误实验输入，纳入本轮唯一修复；没有延后Minor。没有派第二审查代理，修复依据为先复现失败的覆盖测试与完整suite。

运行证据：tests/test_review_regressions.py首次12 failed/1 skipped，修复后12 passed/1 skipped；全套83 passed/2 skipped，跳过均为Windows文件symlink权限。真实目录junction已测试。compileall退出0。

审查未判定的现场范围已逐项裁定，并记录于execution-ledger.md：光学/曝光起点、真实窗口与遮挡、跨电脑/防火墙/Claude、DLL内部和崩溃物理状态。现场暗帧补充了CCD SDK/数据通路证据，没有替代这些边界。
