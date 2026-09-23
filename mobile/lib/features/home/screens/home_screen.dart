import 'package:flutter/material.dart';

import '../../auth/auth_controller.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = AuthController.instance.user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dello'),
        actions: [
          IconButton(
            tooltip: 'Se déconnecter',
            icon: const Icon(Icons.logout),
            onPressed: () => AuthController.instance.logout(),
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Bonjour ${user?.fullName ?? ''}',
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              Text(
                user?.phoneNumber ?? '',
                style: const TextStyle(color: Colors.black54),
              ),
              const SizedBox(height: 32),
              const Text(
                'Les déclarations de documents perdus et trouvés arriveront ici.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.black54),
              ),
            ],
          ),
        ),
      ),
    );
  }
}