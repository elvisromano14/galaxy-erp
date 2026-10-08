import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

class VentasScreen extends StatefulWidget {
  const VentasScreen({super.key});

  @override
  State<VentasScreen> createState() => _VentasScreenState();
}

class _VentasScreenState extends State<VentasScreen> {
  List<dynamic> _facturas = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _cargarFacturas();
  }

  Future<void> _cargarFacturas() async {
    setState(() => _loading = true);
    try {
      final res = await ApiClient().dio.get('/api/v1/ventas/facturas');
      setState(() => _facturas = res.data);
    } catch (_) {
      // Manejo de error
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('Ventas y Facturación', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppTheme.textDark)),
                  Text('Documentos fiscales emitidos y cuentas por cobrar', style: TextStyle(color: AppTheme.textMuted, fontSize: 13)),
                ],
              ),
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('NUEVA FACTURA'),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Expanded(
            child: Card(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _facturas.isEmpty
                      ? const Center(child: Text('No hay facturas registradas.', style: TextStyle(color: AppTheme.textMuted)))
                      : ListView.separated(
                          itemCount: _facturas.length,
                          separatorBuilder: (_, __) => const Divider(height: 1, color: Color(0xFFE2E8F0)),
                          itemBuilder: (context, index) {
                            final f = _facturas[index];
                            return ListTile(
                              leading: const CircleAvatar(
                                backgroundColor: Color(0xFFEFF6FF),
                                child: Icon(Icons.receipt_rounded, color: AppTheme.primaryLight),
                              ),
                              title: Text('Factura: ${f['numero_factura']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                              subtitle: Text('Fecha: ${f['fecha_emision']} | Control: ${f['numero_control']}'),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    '\$${f['total_usd']}',
                                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                                  ),
                                  const SizedBox(width: 12),
                                  IconButton(
                                    icon: const Icon(Icons.picture_as_pdf_rounded, color: Colors.redAccent),
                                    tooltip: 'Descargar PDF SENIAT',
                                    onPressed: () {},
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
            ),
          ),
        ],
      ),
    );
  }
}
