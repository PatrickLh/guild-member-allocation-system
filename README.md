AI生成分配系统，用于工会战人员分配

# 服务器部署方案

## 1、检查是否有运行中的服务

`ps aux | grep gunicorn`

## 2、杀死所有后台进程

`pkill gunicorn`

## 3、进入服务目录

`cd /root/project/guild-member-allocation-system/backend`

## 4、启动服务
`gunicorn -w 2 -b 0.0.0.0:5001 main:app --daemon`

## 备注

需要提前安装python代码运行相关库
`pip3 install flask`
`pip3 install flask_cors`