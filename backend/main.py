"""
游戏工会分组系统 - 后端服务
"""
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import json
import os
import uuid
from copy import deepcopy

app = Flask(__name__)
CORS(app)

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
MEMBERS_FILE = os.path.join(DATA_DIR, 'members.json')
FIRST_GROUP_FILE = os.path.join(DATA_DIR, 'first_group.json')
GROUP_HISTORY_FILE = os.path.join(DATA_DIR, 'group_history.json')

# 前端文件路径
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')


def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def read_members():
    """读取成员信息"""
    if not os.path.exists(MEMBERS_FILE):
        return []
    with open(MEMBERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_members(members):
    """写入成员信息"""
    with open(MEMBERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(members, f, ensure_ascii=False, indent=2)


def read_first_group():
    """读取第一组历史记录 - 返回成员ID到次数的映射"""
    if not os.path.exists(FIRST_GROUP_FILE):
        return {}
    with open(FIRST_GROUP_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_first_group(records):
    """写入第一组历史记录"""
    with open(FIRST_GROUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def read_group_history():
    """读取分组历史"""
    if not os.path.exists(GROUP_HISTORY_FILE):
        return []
    with open(GROUP_HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_group_history(history):
    """写入分组历史"""
    with open(GROUP_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/api/members', methods=['GET'])
def get_members():
    """获取所有成员"""
    members = read_members()
    return jsonify(members)


@app.route('/api/members', methods=['POST'])
def add_member():
    """添加成员"""
    data = request.json
    name = data.get('name', '').strip()
    profession = data.get('profession', '')
    power = data.get('power', 0)

    if not name or not profession or power <= 0:
        return jsonify({'error': '请填写完整的成员信息'}), 400

    valid_professions = ['斗士', '术士', '骑士', '贤者']
    if profession not in valid_professions:
        return jsonify({'error': '无效的职业'}), 400

    members = read_members()
    member = {
        'id': str(uuid.uuid4()),
        'name': name,
        'profession': profession,
        'power': power
    }
    members.append(member)
    write_members(members)

    return jsonify(member)


@app.route('/api/members/<member_id>', methods=['DELETE'])
def delete_member(member_id):
    """删除成员"""
    members = read_members()
    members = [m for m in members if m['id'] != member_id]
    write_members(members)
    return jsonify({'success': True})


@app.route('/api/members/<member_id>', methods=['PUT'])
def update_member(member_id):
    """更新成员信息"""
    data = request.json
    members = read_members()

    for member in members:
        if member['id'] == member_id:
            if 'name' in data:
                member['name'] = data['name']
            if 'profession' in data:
                valid_professions = ['斗士', '术士', '骑士', '贤者']
                if data['profession'] not in valid_professions:
                    return jsonify({'error': '无效的职业'}), 400
                member['profession'] = data['profession']
            if 'power' in data:
                if data['power'] <= 0:
                    return jsonify({'error': '战力必须大于0'}), 400
                member['power'] = data['power']
            break

    write_members(members)
    return jsonify({'success': True})


@app.route('/api/first-group-history', methods=['GET'])
def get_first_group_history():
    """获取第一组历史记录"""
    records = read_first_group()
    return jsonify(records)


@app.route('/api/group', methods=['POST'])
def create_groups():
    """创建分组"""
    data = request.json
    first_group_ids = data.get('firstGroup', [])
    manual_adjustments = data.get('manualAdjustments', [])

    members = read_members()
    if not members:
        return jsonify({'error': '没有成员数据'}), 400

    # 分组逻辑
    groups = auto_group(members, first_group_ids)

    # 应用手动调整
    if manual_adjustments:
        apply_manual_adjustments(groups, manual_adjustments, members)

    return jsonify(groups)


def auto_group(members, first_group_ids):
    """自动分组"""
    # 按战力排序
    sorted_members = sorted(members, key=lambda x: x['power'], reverse=True)

    # 第一组
    first_group = []
    remaining_members = []

    for member in sorted_members:
        if member['id'] in first_group_ids:
            first_group.append(member)
        else:
            remaining_members.append(member)

    groups = []
    if first_group:
        # 第一组自动补全到4人
        while len(first_group) < 4 and remaining_members:
            first_group.append(remaining_members.pop(0))
        groups.append(first_group)

    # 其余分组 - 简化逻辑，直接按顺序分配
    current_group = []

    for member in remaining_members:
        current_group.append(member)

        # 每组4个人
        if len(current_group) == 4:
            groups.append(current_group)
            current_group = []

    # 剩余不足4人的成一组
    if current_group:
        groups.append(current_group)

    return groups


def find_alternative_member(current_member, remaining_members, current_professions, used_ids):
    """寻找不同职业且战力相近的成员"""
    idx = remaining_members.index(current_member)
    current_power = current_member['power']

    for i in range(idx + 1, len(remaining_members)):
        member = remaining_members[i]
        if member['id'] in used_ids:
            continue
        if member['profession'] not in current_professions:
            power_diff_pct = abs(member['power'] - current_power) / current_power
            if power_diff_pct < 0.1:
                return member

    return None


def apply_manual_adjustments(groups, adjustments, all_members):
    """应用手动调整"""
    for adj in adjustments:
        from_id = adj.get('from')
        to_id = adj.get('to')

        # 找到两个成员所在的组
        from_pos = None
        to_pos = None

        for i, group in enumerate(groups):
            for j, member in enumerate(group):
                if member['id'] == from_id:
                    from_pos = (i, j)
                if member['id'] == to_id:
                    to_pos = (i, j)

        if from_pos and to_pos:
            from_group_idx, from_member_idx = from_pos
            to_group_idx, to_member_idx = to_pos
            # 交换两个成员
            groups[from_group_idx][from_member_idx], groups[to_group_idx][to_member_idx] = \
                groups[to_group_idx][to_member_idx], groups[from_group_idx][from_member_idx]


@app.route('/api/save-group-history', methods=['POST'])
def save_group_history():
    """保存分组历史"""
    import datetime
    data = request.json
    groups = data.get('groups', [])
    first_group_ids = data.get('firstGroup', [])

    # 更新第一组历史记录
    if first_group_ids:
        records = read_first_group()
        for member_id in first_group_ids:
            records[member_id] = records.get(member_id, 0) + 1
        write_first_group(records)

    # 保存分组历史
    history = read_group_history()
    history.append({
        'date': datetime.datetime.now().isoformat(),
        'groups': groups
    })
    write_group_history(history)

    return jsonify({'success': True})


@app.route('/api/group-history', methods=['GET'])
def get_group_history():
    """获取分组历史"""
    history = read_group_history()
    return jsonify(history)


@app.route('/api/reset-first-group', methods=['POST'])
def reset_first_group():
    """重置第一组历史记录（所有人都轮过后重新开始）"""
    write_first_group({})
    return jsonify({'success': True})


if __name__ == '__main__':
    ensure_data_dir()
    app.run(debug=True, host='0.0.0.0', port=5001)
else:
    # gunicorn 启动时执行
    ensure_data_dir()
