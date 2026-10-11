import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:goqd_app/app/app.dart';

void main() {
  testWidgets('App 启动渲染登录页', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: GoQDApp()));
    await tester.pump();

    expect(find.text('七德通'), findsWidgets);
    expect(find.text('碰一碰，发现校园新鲜事'), findsOneWidget);
  });

  testWidgets('登录页包含学号与密码输入', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: GoQDApp()));
    await tester.pump();

    expect(find.byType(TextFormField), findsNWidgets(2));
    expect(find.text('登录'), findsOneWidget);
  });
}
