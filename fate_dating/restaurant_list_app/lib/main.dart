import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'restaurant_provider.dart';

void main() {
  runApp(ProviderScope(child: MyApp()));
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Restaurant List',
      home: RestaurantListScreen(),
    );
  }
}

class RestaurantListScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final restaurantList = ref.watch(restaurantListProvider);
    final searchQuery = ref.watch(searchQueryProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text('Restaurant List'),
        bottom: PreferredSize(
          preferredSize: Size.fromHeight(56),
          child: Padding(
            padding: EdgeInsets.all(8.0),
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Search restaurants...',
                border: OutlineInputBorder(),
              ),
              onChanged: (value) {
                ref.read(searchQueryProvider.notifier).state = value;
              },
            ),
          ),
        ),
      ),
      body: restaurantList.when(
        data: (restaurants) {
          final filteredRestaurants = restaurants
              .where((name) => name.toLowerCase().contains(searchQuery.toLowerCase()))
              .toList();

          return ListView.builder(
            itemCount: filteredRestaurants.length,
            itemBuilder: (context, index) {
              return ListTile(
                title: Text(filteredRestaurants[index]),
              );
            },
          );
        },
        loading: () => Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Error loading restaurants')),
      ),
    );
  }
}
