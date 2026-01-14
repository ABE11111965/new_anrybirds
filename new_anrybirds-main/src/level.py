"""
重构后的关卡系统 - 双人对抗模式
每个关卡定义防守方可用的资源数量，而不是预设物体位置
"""

class Level():
    def __init__(self, pigs, columns, beams, space):
        self.pigs = pigs
        self.columns = columns
        self.beams = beams
        self.space = space
        self.number = 0
        self.number_of_birds = 4
        
        # 库存系统 - 防守方可用资源
        self.inventory = {
            'pigs': 0,
            'columns': 0,
            'beams': 0
        }
        
        # 放置的物体列表（用于跟踪）
        self.placed_objects = []
        
        # 星级评分阈值
        self.one_star = 30000
        self.two_star = 40000
        self.three_star = 60000
        
        # 是否为太空模式（低重力）
        self.bool_space = False

    def reset_inventory(self):
        """重置库存"""
        self.inventory = {
            'pigs': 0,
            'columns': 0,
            'beams': 0
        }
        self.placed_objects = []

    def load_level(self):
        """加载关卡 - 设置库存数量"""
        self.reset_inventory()
        try:
            build_name = "build_" + str(self.number)
            getattr(self, build_name)()
        except AttributeError:
            self.number = 0
            build_name = "build_" + str(self.number)
            getattr(self, build_name)()

    def build_0(self):
        """关卡 0 - 新手教学关"""
        self.inventory = {
            'pigs': 2,
            'columns': 4,
            'beams': 2
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 30000
        self.two_star = 40000
        self.three_star = 60000

    def build_1(self):
        """关卡 1 - 简单挑战"""
        self.inventory = {
            'pigs': 1,
            'columns': 4,
            'beams': 1
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 25000
        self.two_star = 35000
        self.three_star = 50000

    def build_2(self):
        """关卡 2 - 双猪防线"""
        self.inventory = {
            'pigs': 2,
            'columns': 4,
            'beams': 2
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 30000
        self.two_star = 45000
        self.three_star = 60000

    def build_3(self):
        """关卡 3 - 三猪要塞"""
        self.inventory = {
            'pigs': 3,
            'columns': 8,
            'beams': 6
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 40000
        self.two_star = 55000
        self.three_star = 75000

    def build_4(self):
        """关卡 4 - 自由布置"""
        self.inventory = {
            'pigs': 3,
            'columns': 0,
            'beams': 0
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 35000
        self.two_star = 50000
        self.three_star = 70000

    def build_5(self):
        """关卡 5 - 木材充足"""
        self.inventory = {
            'pigs': 2,
            'columns': 6,
            'beams': 10
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 35000
        self.two_star = 50000
        self.three_star = 70000

    def build_6(self):
        """关卡 6 - 坚固堡垒"""
        self.inventory = {
            'pigs': 3,
            'columns': 12,
            'beams': 6
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 45000
        self.two_star = 60000
        self.three_star = 80000

    def build_7(self):
        """关卡 7 - 高塔挑战"""
        self.inventory = {
            'pigs': 3,
            'columns': 10,
            'beams': 4
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 40000
        self.two_star = 55000
        self.three_star = 75000

    def build_8(self):
        """关卡 8 - 阶梯结构"""
        self.inventory = {
            'pigs': 3,
            'columns': 8,
            'beams': 8
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 45000
        self.two_star = 60000
        self.three_star = 80000

    def build_9(self):
        """关卡 9 - 双重防线"""
        self.inventory = {
            'pigs': 2,
            'columns': 10,
            'beams': 10
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 40000
        self.two_star = 55000
        self.three_star = 75000

    def build_10(self):
        """关卡 10 - 最终要塞"""
        self.inventory = {
            'pigs': 3,
            'columns': 12,
            'beams': 8
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 50000
        self.two_star = 70000
        self.three_star = 90000

    def build_11(self):
        """关卡 11 - 大师挑战"""
        self.inventory = {
            'pigs': 4,
            'columns': 14,
            'beams': 10
        }
        self.number_of_birds = 4
        if self.bool_space:
            self.number_of_birds = 8
        self.one_star = 60000
        self.two_star = 80000
        self.three_star = 100000

    def can_place(self, item_type):
        """检查是否还能放置该类型物体"""
        return self.inventory.get(item_type, 0) > 0

    def consume_item(self, item_type):
        """消耗一个库存物品"""
        if self.can_place(item_type):
            self.inventory[item_type] -= 1
            return True
        return False

    def get_remaining(self, item_type):
        """获取剩余数量"""
        return self.inventory.get(item_type, 0)

    def all_pigs_placed(self):
        """检查是否所有猪都已放置"""
        return self.inventory['pigs'] == 0

    def get_total_remaining(self):
        """获取总剩余数量"""
        return sum(self.inventory.values())
