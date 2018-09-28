1、dll中是C++接口封装的动态库，不用动
2、py_ctp中是python封装的ctp接口和demo
3、两个demo(test_api和test_multi)，test_api是买单个合约的例子；test_multi是根据配置文件买多个合约的例子，依赖两个配置文件，config里边包含账号信息等，orderBook是需要买的合约和数量
4、py_ctp中除了test_api和test_multi的py文件都是封装的接口，请勿改变
5、demo中根据自己的需求改变相关逻辑和配置文件
6、demo中的接口（已经有简略注释）可以查阅接口说明文档，查看具体含义
7、底层封装使用了海风的ctp，本人（牛进伟）写了demo和封装中的字段注释，使用过程中逻辑问题可以和我探讨（qq,微信:943649129,邮箱:njw128@126.com）
