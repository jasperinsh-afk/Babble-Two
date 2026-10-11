import 'package:flutter/material.dart' hide Page;

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// 住宿生活：宿舍频道 / 失物招领 / 二手交换
/// PRD §3.4 L-001 ~ L-103
class LivingPage extends StatefulWidget {
  const LivingPage({super.key});

  @override
  State<LivingPage> createState() => _LivingPageState();
}

class _LivingPageState extends State<LivingPage> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 3, vsync: this);

  List<DormChannel> _channels = [];
  List<DormPost> _posts = [];
  List<LostFoundItem> _lost = [];
  List<SecondHandItem> _market = [];
  int? _activeChannel;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final channels = await ApiService.dormChannels();
      final lost = await ApiService.lostFound();
      final market = await ApiService.secondHand();
      Page<DormPost>? posts;
      int? first;
      if (channels.isNotEmpty) {
        first = channels.first.id;
        posts = await ApiService.dormPosts(first);
      }
      setState(() {
        _channels = channels;
        _lost = lost.items;
        _market = market.items;
        _activeChannel = first;
        _posts = posts?.items ?? [];
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _switchChannel(int id) async {
    setState(() => _activeChannel = id);
    try {
      final posts = await ApiService.dormPosts(id);
      setState(() => _posts = posts.items);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('住宿生活'),
        bottom: TabBar(
          controller: _tabs,
          labelColor: GoQDColors.primary,
          unselectedLabelColor: GoQDColors.textSecondary,
          indicatorColor: GoQDColors.primary,
          tabs: const [
            Tab(text: '宿舍圈'),
            Tab(text: '失物招领'),
            Tab(text: '二手交换'),
          ],
        ),
      ),
      body: _loading
          ? const LoadingView()
          : (_error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : TabBarView(
                  controller: _tabs,
                  children: [_buildChannels(), _buildLost(), _buildMarket()],
                )),
    );
  }

  Widget _buildChannels() {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.only(bottom: 32),
        children: [
          SizedBox(
            height: 44,
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              scrollDirection: Axis.horizontal,
              children: [
                for (final c in _channels) ...[
                  ChoiceChip(
                    label: Text('${c.name} · ${c.scopeLabel}'),
                    selected: _activeChannel == c.id,
                    showCheckmark: false,
                    onSelected: (_) => _switchChannel(c.id),
                    selectedColor: GoQDColors.primary,
                    backgroundColor: Colors.white,
                    labelStyle: TextStyle(
                      color: _activeChannel == c.id
                          ? Colors.white
                          : GoQDColors.textSecondary,
                    ),
                  ),
                  const SizedBox(width: 8),
                ],
              ],
            ),
          ),
          if (_posts.isEmpty)
            const Padding(
              padding: EdgeInsets.all(40),
              child: Center(
                  child: Text('本频道暂无帖子',
                      style: TextStyle(color: GoQDColors.textSecondary))),
            )
          else
            for (final p in _posts)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: GoQDColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(p.authorNickname,
                        style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: GoQDColors.primary)),
                    const SizedBox(height: 6),
                    Text(p.content, style: const TextStyle(fontSize: 14, height: 1.5)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Icon(Icons.favorite_border, size: 14,
                            color: GoQDColors.textSecondary),
                        const SizedBox(width: 4),
                        Text('${p.likeCount}',
                            style: const TextStyle(
                                fontSize: 12, color: GoQDColors.textSecondary)),
                        const SizedBox(width: 16),
                        const Icon(Icons.mode_comment_outlined, size: 14,
                            color: GoQDColors.textSecondary),
                        const SizedBox(width: 4),
                        Text('${p.replyCount}',
                            style: const TextStyle(
                                fontSize: 12, color: GoQDColors.textSecondary)),
                      ],
                    ),
                  ],
                ),
              ),
        ],
      ),
    );
  }

  Widget _buildLost() {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.only(bottom: 32),
        children: [
          if (_lost.isEmpty)
            const Padding(
              padding: EdgeInsets.all(40),
              child: Center(
                  child: Text('暂无失物信息',
                      style: TextStyle(color: GoQDColors.textSecondary))),
            )
          else
            for (final i in _lost)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: GoQDColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        TagChip(
                            text: i.kind == 'lost' ? '寻物' : '招领',
                            color: i.kind == 'lost' ? GoQDColors.warning : GoQDColors.accent),
                        const Spacer(),
                        if (i.isResolved) const TagChip(text: '已解决', color: GoQDColors.accent),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(i.title,
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                    if (i.description != null) ...[
                      const SizedBox(height: 4),
                      Text(i.description!,
                          style: const TextStyle(
                              fontSize: 13, color: GoQDColors.textSecondary)),
                    ],
                    if (i.location != null) ...[
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          const Icon(Icons.place_outlined, size: 14,
                              color: GoQDColors.textSecondary),
                          const SizedBox(width: 4),
                          Text(i.location!,
                              style: const TextStyle(
                                  fontSize: 12, color: GoQDColors.textSecondary)),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
        ],
      ),
    );
  }

  Widget _buildMarket() {
    return RefreshIndicator(
      onRefresh: _load,
      child: GridView.builder(
        padding: const EdgeInsets.all(16),
        shrinkWrap: true,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 10,
          mainAxisSpacing: 10,
          childAspectRatio: 0.86,
        ),
        itemCount: _market.length,
        itemBuilder: (_, i) {
          final m = _market[i];
          return Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: GoQDColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Center(
                    child: Icon(Icons.image_outlined, size: 40,
                        color: GoQDColors.textSecondary.withValues(alpha: 0.4)),
                  ),
                ),
                const SizedBox(height: 8),
                Text(m.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(m.priceText,
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700,
                        color: GoQDColors.danger)),
                if (m.isSold) const TagChip(text: '已售', color: GoQDColors.textSecondary),
              ],
            ),
          );
        },
      ),
    );
  }
}
