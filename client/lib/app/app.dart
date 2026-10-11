import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/deep_link_handler.dart';
import '../features/auth/auth_provider.dart';
import 'router.dart';
import 'theme.dart';

class GoQDApp extends ConsumerStatefulWidget {
  const GoQDApp({super.key});

  @override
  ConsumerState<GoQDApp> createState() => _GoQDAppState();
}

class _GoQDAppState extends ConsumerState<GoQDApp> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      await ref.read(authStateProvider).bootstrap();

      // 联网后补报本地暂存数据
      await DeepLinkHandler.syncPendingVotes();
      await DeepLinkHandler.syncPendingTaps();

      final router = ref.read(routerProvider);
      await DeepLinkHandler().init(router);
    });
  }

  @override
  Widget build(BuildContext context) {
    final GoRouter router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: '七德通 GoQD',
      debugShowCheckedModeBanner: false,
      theme: GoQDTheme.light(),
      routerConfig: router,
    );
  }
}
