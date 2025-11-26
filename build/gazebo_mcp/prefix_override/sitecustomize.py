import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/koen/workspaces/hackathon-git/ros2_gazebo_mcp/install/gazebo_mcp'
