import 'package:flutter/material.dart' hide Banner;
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// 首页（发现）：Banner + 今日头条 + 热门投票 + 推荐活动 + 社团精选
/// PRD §3.5 H-001 ~ H-008
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  HomeFeed? _feed;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _feed = await ApiService.homeFeed();
    } catch (e) {
      _error = e.toString();
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('发现'),
        actions: [
          IconButton(
            icon: const Icon(Icons.nfc_outlined),
            tooltip: '碰一碰',
            onPressed: () => context.push('/nfc'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const LoadingView()
            : (_error != null
                ? ErrorView(message: _error!, onRetry: _load)
                : _buildBody()),
      ),
    );
  }

  Widget _buildBody() {
    final feed = _feed!;
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        // H-001 Banner 轮播
        if (feed.banners.isNotEmpty) _BannerCarousel(banners: feed.banners),

        // H-002 今日头条
        if (feed.todayPoll != null) ...[
          const SectionHeader(title: '今日头条'),
          _TodayCard(poll: feed.todayPoll!),
        ],

        // H-003 热门投票
        if (feed.hotPolls.isNotEmpty) ...[
          SectionHeader(
            title: '热门投票',
            action: '查看全部',
            onAction: () => context.go('/vote'),
          ),
          SizedBox(
            height: 168,
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              scrollDirection: Axis.horizontal,
              itemCount: feed.hotPolls.length,
              separatorBuilder: (_, __) => const SizedBox(width: 10),
              itemBuilder: (_, i) => SizedBox(
                width: 260,
                child: PollCard(
                  poll: feed.hotPolls[i],
                  onTap: () => context.push('/vote/${feed.hotPolls[i].id}'),
                ),
              ),
            ),
          ),
        ],

        // H-004 推荐活动
        if (feed.recommendedEvents.isNotEmpty) ...[
          SectionHeader(
            title: '近期活动',
            action: '去日历',
            onAction: () => context.go('/calendar'),
          ),
          for (final e in feed.recommendedEvents)
            EventCard(event: e, onTap: () => context.push('/calendar')),
        ],

        // H-005 社团精选
        if (feed.featuredClubs.isNotEmpty) ...[
          SectionHeader(
            title: '社团精选',
            action: '查看全部',
            onAction: () => context.go('/club'),
          ),
          for (final c in feed.featuredClubs)
            ClubCard(club: c, onTap: () => context.push('/club/${c.id}')),
        ],
      ],
    );
  }
}

class _BannerCarousel extends StatefulWidget {
  const _BannerCarousel({required this.banners});

  final List<Banner> banners;

  @override
  State<_BannerCarousel> createState() => _BannerCarouselState();
}

class _BannerCarouselState extends State<_BannerCarousel> {
  final _controller = PageController(viewportFraction: 0.92);
  int _page = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          height: 140,
          child: PageView.builder(
            controller: _controller,
            onPageChanged: (i) => setState(() => _page = i),
            itemCount: widget.banners.length,
            itemBuilder: (_, i) {
              final b = widget.banners[i];
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [GoQDColors.primary, GoQDColors.primaryLight],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                    ),
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(b.title,
                            style: const TextStyle(
                                color: Colors.white, fontSize: 19, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 6),
                        Text(b.subtitle,
                            style: const TextStyle(color: Colors.white70, fontSize: 13)),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(widget.banners.length, (i) {
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 3),
              width: _page == i ? 16 : 6,
              height: 6,
              decoration: BoxDecoration(
                color: _page == i ? GoQDColors.primary : GoQDColors.border,
                borderRadius: BorderRadius.circular(3),
              ),
            );
          }),
        ),
      ],
    );
  }
}

class _TodayCard extends StatelessWidget {
  const _TodayCard({required this.poll});

  final Poll poll;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => context.push('/vote/${poll.id}'),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: LinearGradient(
              colors: [
                GoQDColors.primary.withValues(alpha: 0.08),
                Colors.white,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.local_fire_department,
                      size: 18, color: GoQDColors.danger),
                  const SizedBox(width: 6),
                  const Text('今日头条',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700,
                          color: GoQDColors.danger)),
                  const Spacer(),
                  Text(poll.remainingText,
                      style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
                ],
              ),
              const SizedBox(height: 10),
              Text(poll.title,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              if (poll.description != null) ...[
                const SizedBox(height: 8),
                Text(poll.description!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13, color: GoQDColors.textSecondary)),
              ],
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      onPressed: () => context.push('/vote/${poll.id}'),
                      child: Text(poll.hasVoted ? '查看结果' : '立即投票'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
