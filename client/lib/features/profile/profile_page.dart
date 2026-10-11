import 'package:flutter/material.dart' hide Badge;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../features/auth/auth_provider.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// 个人中心（PRD §3.7 U-001 ~ U-009）
class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage> {
  List<Badge> _badges = [];
  List<Event> _events = [];
  List<CasRecord> _cas = [];
  List<Club> _clubs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        ApiService.badges().catchError((_) => <Badge>[]),
        ApiService.myEvents().catchError((_) => <Event>[]),
        ApiService.myCas().catchError((_) => <CasRecord>[]),
        ApiService.myClubs().catchError((_) => <Club>[]),
      ]);
      setState(() {
        _badges = results[0] as List<Badge>;
        _events = results[1] as List<Event>;
        _cas = results[2] as List<CasRecord>;
        _clubs = results[3] as List<Club>;
      });
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authStateProvider).user;
    final earned = _badges.where((b) => b.earned).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('我的'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: '退出登录',
            onPressed: () => ref.read(authStateProvider).logout(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.only(bottom: 32),
          children: [
            // 个人信息
            Container(
              padding: const EdgeInsets.all(20),
              color: Colors.white,
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 34,
                    backgroundColor: GoQDColors.primary.withValues(alpha: 0.12),
                    child: Text(
                      (user?.nickname.isNotEmpty ?? false)
                          ? user!.nickname.substring(0, 1)
                          : '我',
                      style: const TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.w700,
                          color: GoQDColors.primary),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(user?.nickname ?? '未登录',
                            style: const TextStyle(
                                fontSize: 18, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        Text(
                          [
                            if (user?.grade != null) '${user!.grade} 年级',
                            if (user?.dormitory != null) user!.dormitory,
                          ].join(' · '),
                          style: const TextStyle(
                              fontSize: 12, color: GoQDColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // 数据概览
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: GoQDColors.border),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _MiniStat(label: '勋章', value: '$earned'),
                    _MiniStat(label: '我的社团', value: '${_clubs.length}'),
                    _MiniStat(label: '我的活动', value: '${_events.length}'),
                    _MiniStat(label: 'CAS 记录', value: '${_cas.length}'),
                  ],
                ),
              ),
            ),

            // 勋章墙（U-006）
            const SectionHeader(title: '勋章墙'),
            if (_loading)
              const Padding(padding: EdgeInsets.all(24), child: LoadingView())
            else
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                    crossAxisSpacing: 10,
                    mainAxisSpacing: 10,
                    childAspectRatio: 0.92,
                  ),
                  itemCount: _badges.length,
                  itemBuilder: (_, i) => _BadgeTile(badge: _badges[i]),
                ),
              ),

            const SectionHeader(title: '我的活动'),
            if (_events.isEmpty)
              const Padding(
                padding: EdgeInsets.all(24),
                child: Center(
                    child: Text('还没有报名活动',
                        style: TextStyle(color: GoQDColors.textSecondary))),
              )
            else
              for (final e in _events.take(5)) EventCard(event: e),

            const SectionHeader(title: 'CAS 履历'),
            if (_cas.isEmpty)
              const Padding(
                padding: EdgeInsets.all(24),
                child: Center(
                    child: Text('暂无 CAS 记录',
                        style: TextStyle(color: GoQDColors.textSecondary))),
              )
            else
              for (final c in _cas.take(5))
                Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: GoQDColors.accent.withValues(alpha: 0.12),
                      child: Text(c.casType,
                          style: const TextStyle(
                              color: GoQDColors.accent,
                              fontWeight: FontWeight.w700)),
                    ),
                    title: Text(c.title),
                    subtitle: Text('${c.role == 'participant' ? '参与者' : c.role}'),
                  ),
                ),

            const SizedBox(height: 20),

            // 设置项
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.meeting_room_outlined),
                    title: const Text('住宿生活'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push('/living'),
                  ),
                  ListTile(
                    leading: const Icon(Icons.notifications_none),
                    title: const Text('消息通知'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {},
                  ),
                  ListTile(
                    leading: const Icon(Icons.privacy_tip_outlined),
                    title: const Text('隐私与注销账号'),
                    subtitle: const Text('注销将清除个人数据，保留匿名化投票统计',
                        style: TextStyle(fontSize: 11)),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => _confirmDelete(context),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('注销账号'),
        content: const Text(
            '注销后你的个人资料、社团关系、报名记录将被清除。\n'
            '已投出的票会以匿名形式保留在统计中，不受影响。\n\n此操作不可撤销。'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: GoQDColors.danger),
            child: const Text('确认注销'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(authStateProvider).logout();
  }
}

class _MiniStat extends StatelessWidget {
  const _MiniStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Text(value,
              style: const TextStyle(
                  fontSize: 20, fontWeight: FontWeight.w700, color: GoQDColors.primary)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
        ],
      );
}

class _BadgeTile extends StatelessWidget {
  const _BadgeTile({required this.badge});

  final Badge badge;

  @override
  Widget build(BuildContext context) {
    final color = switch (badge.rarity) {
      'legendary' => const Color(0xFFD98008),
      'rare' => GoQDColors.primary,
      _ => GoQDColors.textSecondary,
    };
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: badge.earned ? color.withValues(alpha: 0.4) : GoQDColors.border,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            badge.earned ? Icons.military_tech : Icons.lock_outline,
            size: 32,
            color: badge.earned ? color : GoQDColors.textSecondary.withValues(alpha: 0.35),
          ),
          const SizedBox(height: 6),
          Text(badge.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: badge.earned ? GoQDColors.textPrimary : GoQDColors.textSecondary,
              )),
          const SizedBox(height: 2),
          Text(badge.earned ? '已获得' : '待解锁',
              style: const TextStyle(fontSize: 10, color: GoQDColors.textSecondary)),
        ],
      ),
    );
  }
}
