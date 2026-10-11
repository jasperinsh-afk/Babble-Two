import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../app/theme.dart';

/// 五个一级 Tab：首页(发现) / 投票 / 社团 / 日历 / 我的
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  static const _tabs = [
    (icon: Icons.home_outlined, active: Icons.home, label: '发现'),
    (icon: Icons.how_to_vote_outlined, active: Icons.how_to_vote, label: '投票'),
    (icon: Icons.groups_outlined, active: Icons.groups, label: '社团'),
    (icon: Icons.calendar_month_outlined, active: Icons.calendar_month, label: '日历'),
    (icon: Icons.person_outline, active: Icons.person, label: '我的'),
  ];

  void _onTap(int index) {
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: _onTap,
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        indicatorColor: GoQDColors.primary.withValues(alpha: 0.12),
        destinations: [
          for (final t in _tabs)
            NavigationDestination(icon: Icon(t.icon), selectedIcon: Icon(t.active), label: t.label),
        ],
      ),
    );
  }
}
