import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';
import 'features/auth/auth_controller.dart';
import 'features/auth/screens/login_screen.dart';
import 'features/home/screens/home_screen.dart';

void main() {
  runApp(const DelloApp());
}

class DelloApp extends StatelessWidget {
  const DelloApp({super.key});

  static final navigatorKey = GlobalKey<NavigatorState>();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Dello',
      debugShowCheckedModeBanner: false,
      navigatorKey: navigatorKey,
      theme: AppTheme.light,
      home: const AuthGate(),
    );
  }
}

/// Aiguille vers la connexion ou l'accueil selon l'état de la session.
/// Centraliser ça ici garantit qu'une session expirée ramène toujours
/// à la connexion, depuis n'importe quel écran.
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  @override
  void initState() {
    super.initState();
    AuthController.instance.bootstrap();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AuthController.instance,
      builder: (context, _) {
        // Une session perdue peut survenir depuis n'importe quel écran :
        // on revient à la racine pour que la connexion ne s'affiche pas
        // sous une pile d'écrans devenus inaccessibles.
        if (AuthController.instance.status == AuthStatus.unauthenticated) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            DelloApp.navigatorKey.currentState?.popUntil((route) => route.isFirst);
          });
        }

        switch (AuthController.instance.status) {
          case AuthStatus.checking:
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          case AuthStatus.authenticated:
            return const HomeScreen();
          case AuthStatus.unauthenticated:
            return const LoginScreen();
        }
      },
    );
  }
}