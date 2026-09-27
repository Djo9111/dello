import 'package:flutter/material.dart';

import '../../auth/auth_controller.dart';
import '../../reports/screens/my_reports_screen.dart';
import '../../reports/screens/reports_list_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  static const _titles = ['Rechercher', 'Mes déclarations', 'Profil'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_titles[_index])),
      body: IndexedStack(
        index: _index,
        children: const [
          ReportsListScreen(),
          MyReportsScreen(),
          _ProfileTab(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (index) => setState(() => _index = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.search_outlined),
            selectedIcon: Icon(Icons.search),
            label: 'Rechercher',
          ),
          NavigationDestination(
            icon: Icon(Icons.description_outlined),
            selectedIcon: Icon(Icons.description),
            label: 'Mes déclarations',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profil',
          ),
        ],
      ),
    );
  }
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab();

  @override
  Widget build(BuildContext context) {
    final user = AuthController.instance.user;

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text(
          user?.fullName ?? '',
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text(
          user?.phoneNumber ?? '',
          style: const TextStyle(color: Colors.black54),
        ),
        const SizedBox(height: 32),
        OutlinedButton.icon(
          onPressed: () => AuthController.instance.logout(),
          icon: const Icon(Icons.logout),
          label: const Text('Se déconnecter'),
          style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
        ),
      ],
    );
  }
}