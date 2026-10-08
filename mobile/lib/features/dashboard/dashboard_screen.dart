import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../ventas/ventas_screen.dart';
import '../inventario/inventario_screen.dart';
import '../sync/sync_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _selectedIndex = 0;

  final List<Widget> _screens = const [
    _DashboardHome(),
    VentasScreen(),
    InventarioScreen(),
    SyncScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0.5,
        title: Row(
          children: [
            const Icon(Icons.rocket_launch_rounded, color: AppTheme.primary),
            const SizedBox(width: 8),
            Text('GALAXY ERP [${ApiClient().tenantSlug?.toUpperCase() ?? "TENANT"}]',
                style: const TextStyle(color: AppTheme.textDark, fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: AppTheme.textMuted),
            onPressed: () {
              ApiClient().clearSession();
              Navigator.of(context).pushReplacementNamed('/');
            },
          ),
        ],
      ),
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: _selectedIndex,
            onDestinationSelected: (idx) => setState(() => _selectedIndex = idx),
            labelType: NavigationRailLabelType.all,
            backgroundColor: Colors.white,
            selectedIconTheme: const IconThemeData(color: AppTheme.primary),
            unselectedIconTheme: const IconThemeData(color: AppTheme.textMuted),
            destinations: const [
              NavigationRailDestination(icon: Icon(Icons.dashboard_rounded), label: Text('Tablero')),
              NavigationRailDestination(icon: Icon(Icons.point_of_sale_rounded), label: Text('Ventas')),
              NavigationRailDestination(icon: Icon(Icons.inventory_2_rounded), label: Text('Inventario')),
              NavigationRailDestination(icon: Icon(Icons.sync_rounded), label: Text('Preventa')),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1, color: Color(0xFFE2E8F0)),
          Expanded(child: _screens[_selectedIndex]),
        ],
      ),
    );
  }
}

class _DashboardHome extends StatelessWidget {
  const _DashboardHome();

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Indicadores de Gestión',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppTheme.textDark)),
          const Text('Resumen consolidado en tiempo real', style: TextStyle(color: AppTheme.textMuted, fontSize: 13)),
          const SizedBox(height: 20),
          Row(
            children: const [
              Expanded(child: _KpiCard(title: 'Ventas del Mes', value: '\$12,450.00', icon: Icons.trending_up_rounded, color: Colors.blue)),
              SizedBox(width: 16),
              Expanded(child: _KpiCard(title: 'Por Cobrar (CxC)', value: '\$3,120.00', icon: Icons.account_balance_wallet_rounded, color: Colors.amber)),
              SizedBox(width: 16),
              Expanded(child: _KpiCard(title: 'Por Pagar (CxP)', value: '\$1,850.00', icon: Icons.receipt_long_rounded, color: Colors.purple)),
              SizedBox(width: 16),
              Expanded(child: _KpiCard(title: 'Alertas de Stock', value: '4 ítems', icon: Icons.warning_amber_rounded, color: Colors.red)),
            ],
          ),
        ],
      ),
    );
  }
}

class _KpiCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final MaterialColor color;

  const _KpiCard({required this.title, required this.value, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: const TextStyle(color: AppTheme.textMuted, fontSize: 13, fontWeight: FontWeight.w600)),
                CircleAvatar(
                  backgroundColor: color.shade50,
                  radius: 18,
                  child: Icon(icon, color: color.shade700, size: 20),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppTheme.textDark)),
          ],
        ),
      ),
    );
  }
}
